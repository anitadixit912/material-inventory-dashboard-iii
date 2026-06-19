'use strict';

const cds = require('@sap/cds');
const { mockStockData } = require('../test/data/material-stock-mock');

// Agent service URL — override via env var when deployed
const AGENT_URL = process.env.AGENT_SERVICE_URL || 'http://localhost:5000';

// ── In-memory threshold cache ─────────────────────────────────────────────
// Avoids dispatching UPDATE/SELECT through the service layer (which would
// be blocked by the @readonly annotation on StockThresholdConfig).
// Seeded from the database on first request; updated in-place by updateThreshold.
let _thresholdPct = null; // null = not yet loaded

async function loadThreshold(db) {
  try {
    const rows = await db.run(SELECT.from('material_stock_StockThresholdConfig').where({ id: 1 }));
    if (rows && rows.length > 0) {
      _thresholdPct = Number(rows[0].safetyStockPct);
      cds.log('stock-service').info(`Threshold loaded from DB: ${_thresholdPct}%`);
    }
  } catch (e) {
    cds.log('stock-service').warn('Could not load threshold from DB, using default 20%:', e.message);
  }
  if (_thresholdPct === null) _thresholdPct = 20;
  return _thresholdPct;
}

async function saveThreshold(db, pct) {
  try {
    const rows = await db.run(SELECT.from('material_stock_StockThresholdConfig').where({ id: 1 }));
    if (rows && rows.length > 0) {
      await db.run(UPDATE('material_stock_StockThresholdConfig').set({ safetyStockPct: pct }).where({ id: 1 }));
    } else {
      await db.run(INSERT.into('material_stock_StockThresholdConfig').entries({ id: 1, safetyStockPct: pct }));
    }
  } catch (e) {
    // Persist is best-effort; in-memory cache is the source of truth
    cds.log('stock-service').warn('Could not persist threshold to DB:', e.message);
  }
}

module.exports = class StockService extends cds.ApplicationService {

  async init() {
    const { MaterialStockView, StockThresholdConfig } = this.entities;
    const db = await cds.connect.to('db');

    // Seed the in-memory threshold from the database on startup
    await loadThreshold(db);

    // ── READ MaterialStockView ──────────────────────────────────────────────
    this.on('READ', MaterialStockView, async (req) => {
      // 1. Use in-memory threshold (always current — updated by updateThreshold action)
      const safetyStockPct = _thresholdPct !== null ? _thresholdPct : 20;

      // 2. In production: fetch live data from S/4HANA via external service.
      //    For local development, use mock data.
      let rawStock;
      try {
        const s4 = await cds.connect.to('API_MATERIAL_STOCK_SRV');
        const { A_MatlStkInAcctModType } = s4.entities;
        rawStock = await s4.run(
          SELECT.from(A_MatlStkInAcctModType).columns(
            'Material', 'Plant', 'StorageLocation', 'MaterialBaseUnit',
            'MatlWrhsStkQtyInMatlBaseUnit'
          )
        );
        // Map external fields to our view shape
        rawStock = rawStock.map(r => ({
          Material        : r.Material,
          Plant           : r.Plant,
          StorageLocation : r.StorageLocation,
          BaseUnit        : r.MaterialBaseUnit,
          StockQuantity   : Number(r.MatlWrhsStkQtyInMatlBaseUnit || 0),
          // ReorderPoint and SafetyStock are not in this API — use 0 as fallback
          ReorderPoint    : 0,
          SafetyStock     : 0,
          MaterialDescription: '',
        }));
      } catch {
        // Fall back to mock data when no real destination is configured.
        // WARNING: Mock data is being used — real S/4HANA destination (S4HANA_MATERIAL_STOCK)
        // is unavailable. Do NOT use mock data in a production environment.
        cds.log('stock-service').warn(
          'SECURITY WARNING: Falling back to mock stock data — S4HANA_MATERIAL_STOCK destination ' +
          'is not configured. Configure the destination before going to production.'
        );
        rawStock = mockStockData.map(r => ({
          Material            : r.Material,
          Plant               : r.Plant,
          StorageLocation     : r.StorageLocation,
          MaterialDescription : r.MaterialDescription,
          StockQuantity       : r.StockQuantity,
          BaseUnit            : r.BaseUnit,
          ReorderPoint        : r.ReorderPoint,
          SafetyStock         : r.SafetyStock,
        }));
      }

      // 3. Classify each material
      const classified = rawStock.map(item => classify(item, safetyStockPct));

      // 4. Apply OData $filter if present (StockStatus eq '...')
      let result = classified;
      const filter = req.query.SELECT?.where;
      if (filter) {
        result = applyFilter(classified, filter);
      }

      // 5. Log milestone
      console.log(`M1.achieved: material stock data retrieved successfully — ${rawStock.length} records loaded`);
      console.log(`M2.achieved: stock classification complete — ${result.filter(r => r.StockStatus === 'SUFFICIENT').length} sufficient, ${result.filter(r => r.StockStatus === 'NEARLY_OUT_OF_STOCK').length} nearly out of stock`);

      return result;
    });

    // ── UPDATETHRESHOLD action — controlled write path for StockThresholdConfig ──
    this.on('updateThreshold', async (req) => {
      const { safetyStockPct } = req.data;
      const pct = Number(safetyStockPct);
      if (isNaN(pct) || pct < 0 || pct > 100) {
        req.error(400, 'safetyStockPct must be a number between 0 and 100.');
        return;
      }
      // Update in-memory cache immediately — this is what the READ handler uses
      _thresholdPct = pct;
      // Persist to DB best-effort (async, don't block the response)
      saveThreshold(db, pct).catch(() => {});
      console.log(`Threshold updated to ${pct}% (in-memory)`);
      return pct;
    });

    // ── CHAT action — proxy to Stock Advisor Agent ─────────────────────────
    this.on('chat', async (req) => {
      const { message, contextId } = req.data;

      // Server-side guard: reject messages exceeding the 1000-char limit
      if (!message || message.trim().length === 0) {
        req.error(400, 'Message must not be empty.');
        return;
      }
      if (message.length > 1000) {
        req.error(400, 'Message exceeds maximum allowed length of 1000 characters.');
        return;
      }

      const threadId = contextId || `thread-${Date.now()}`;

      try {
        // Try calling the Python A2A agent
        const response = await callAgent(message, threadId);
        return response;
      } catch (err) {
        // Agent not available — fall back to rule-based recommendations
        cds.log('stock-service').warn('Agent unavailable, using rule-based fallback:', err.message);
        return ruleBasedRecommendation(message, await this.getClassifiedStock());
      }
    });

    await super.init();
  }

  /** Helper: get classified stock data (reused by fallback) */
  async getClassifiedStock() {
    const safetyStockPct = _thresholdPct !== null ? _thresholdPct : 20;
    return mockStockData.map(item => classify(item, safetyStockPct));
  }
};

/**
 * Format a RiskReason code into a human-readable explanation with actual values.
 * e.g. BOTH → "Below Reorder Point (stock 1 < reorder 10) AND Below Safety Stock threshold (stock 1 < 20% of 30 = 6)"
 */
function formatRiskReason(riskReason, stock, reorderPoint, safetyStock, safetyStockPct = 20) {
  const ropLine  = `Below Reorder Point (stock ${stock} < reorder point ${reorderPoint})`;
  const ssThresh = Math.round(safetyStock * safetyStockPct / 100);
  const ssLine   = `Below Safety Stock threshold (stock ${stock} < ${safetyStockPct}% of safety stock ${safetyStock} = ${ssThresh})`;

  switch (riskReason) {
    case 'REORDER_POINT_BREACH':    return ropLine;
    case 'SAFETY_STOCK_PCT_BREACH': return ssLine;
    case 'BOTH':                    return `${ropLine} AND ${ssLine}`;
    default:                        return riskReason.replace(/_/g, ' ');
  }
}

/**
 * Classify a stock item as SUFFICIENT or NEARLY_OUT_OF_STOCK based on:
 * 1. Stock below reorder point
 * 2. Stock below (safetyStock * safetyStockPct / 100)
 */
function classify(item, safetyStockPct) {
  const qty          = Number(item.StockQuantity)  || 0;
  const reorderPoint = Number(item.ReorderPoint)   || 0;
  const safetyStock  = Number(item.SafetyStock)    || 0;

  const belowReorderPoint  = qty < reorderPoint;
  const safetyStockThresh  = safetyStock * safetyStockPct / 100;
  const belowSafetyStockPct = safetyStock > 0 && qty < safetyStockThresh;

  let StockStatus = 'SUFFICIENT';
  let RiskReason  = null;

  if (belowReorderPoint && belowSafetyStockPct) {
    StockStatus = 'NEARLY_OUT_OF_STOCK';
    RiskReason  = 'BOTH';
  } else if (belowReorderPoint) {
    StockStatus = 'NEARLY_OUT_OF_STOCK';
    RiskReason  = 'REORDER_POINT_BREACH';
  } else if (belowSafetyStockPct) {
    StockStatus = 'NEARLY_OUT_OF_STOCK';
    RiskReason  = 'SAFETY_STOCK_PCT_BREACH';
  }

  const RiskDescription = RiskReason
    ? formatRiskReason(RiskReason, qty, reorderPoint, safetyStock, safetyStockPct)
    : null;

  return { ...item, StockStatus, RiskReason, RiskDescription };
}

/**
 * Fetch a client-credentials Bearer token from XSUAA.
 * Reads credentials from VCAP_SERVICES (bound xsuaa instance).
 * Returns the access_token string, or null if XSUAA is not configured.
 */
async function fetchXsuaaToken() {
  try {
    const vcap = JSON.parse(process.env.VCAP_SERVICES || '{}');
    const xsuaaBinding = (vcap.xsuaa || [])[0];
    if (!xsuaaBinding) {
      cds.log('stock-service').warn('No XSUAA binding found — calling agent without token');
      return null;
    }
    const { clientid, clientsecret, url } = xsuaaBinding.credentials;
    const tokenUrl = `${url}/oauth/token`;
    const parsedUrl = new URL(tokenUrl);
    const body = `grant_type=client_credentials&client_id=${encodeURIComponent(clientid)}&client_secret=${encodeURIComponent(clientsecret)}`;

    return new Promise((resolve, reject) => {
      const transport = require('https');
      const opts = {
        hostname: parsedUrl.hostname,
        port    : 443,
        path    : parsedUrl.pathname,
        method  : 'POST',
        headers : {
          'Content-Type'  : 'application/x-www-form-urlencoded',
          'Content-Length': Buffer.byteLength(body),
        },
        timeout: 10000,
      };
      const req = transport.request(opts, (res) => {
        let raw = '';
        res.on('data', chunk => { raw += chunk; });
        res.on('end', () => {
          try {
            const parsed = JSON.parse(raw);
            if (parsed.access_token) {
              resolve(parsed.access_token);
            } else {
              cds.log('stock-service').warn('XSUAA token response missing access_token:', raw.slice(0, 200));
              resolve(null);
            }
          } catch (e) {
            reject(new Error('Failed to parse XSUAA token response: ' + e.message));
          }
        });
      });
      req.on('error',   reject);
      req.on('timeout', () => { req.destroy(); reject(new Error('XSUAA token request timed out')); });
      req.write(body);
      req.end();
    });
  } catch (e) {
    cds.log('stock-service').warn('fetchXsuaaToken error:', e.message);
    return null;
  }
}

/**
 * Send a message to the Stock Advisor Agent via A2A protocol.
 * Returns the agent's final text response.
 * Supports both http:// (local dev) and https:// (deployed) agent URLs.
 * Attaches a Bearer token from XSUAA when available.
 */
async function callAgent(message, contextId) {
  const taskId   = `task-${Date.now()}`;
  const payload  = {
    jsonrpc: '2.0',
    id: taskId,
    method: 'message/send',
    params: {
      message: {
        messageId: taskId,
        contextId: contextId,
        role: 'user',
        parts: [{ type: 'text', text: message }],
      },
    },
  };

  // Fetch XSUAA token for authenticating against the protected agent endpoint
  const token = await fetchXsuaaToken();

  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(`${AGENT_URL}/`);
    const isHttps   = parsedUrl.protocol === 'https:';
    const transport = isHttps ? require('https') : require('http');
    const defaultPort = isHttps ? 443 : 5000;
    const body = JSON.stringify(payload);
    const headers = {
      'Content-Type'  : 'application/json',
      'Content-Length': Buffer.byteLength(body),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const opts = {
      hostname: parsedUrl.hostname,
      port    : Number(parsedUrl.port) || defaultPort,
      path    : parsedUrl.pathname,
      method  : 'POST',
      headers,
      timeout : 30000,
    };
    const req = transport.request(opts, (res) => {
      let raw = '';
      res.on('data', chunk => { raw += chunk; });
      res.on('end', () => {
        if (res.statusCode >= 400) {
          reject(new Error(`Agent returned HTTP ${res.statusCode}: ${raw.slice(0, 200)}`));
          return;
        }
        try {
          const parsed = JSON.parse(raw);
          // Extract text from A2A message/send response
          // New format: result.parts[] or result.message.parts[]
          const result = parsed?.result;
          const parts  =
            result?.parts ||
            result?.message?.parts ||
            result?.artifacts?.flatMap(a => a.parts || []) ||
            [];
          const text = parts
            .filter(p => p.type === 'text' || p.kind === 'text')
            .map(p => p.text)
            .join('\n') || 'No response from agent.';
          cds.log('stock-service').info('Agent response received successfully');
          resolve(text);
        } catch (e) {
          reject(new Error('Failed to parse agent response: ' + e.message));
        }
      });
    });
    req.on('error',   reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Agent request timed out')); });
    req.write(body);
    req.end();
  });
}

/**
 * Rule-based fallback: answer common stock questions from classified data.
 * Handles: specific material lookups, plant queries, summary, critical, reorder.
 */
function ruleBasedRecommendation(message, stockData) {
  const q        = (message || '').toLowerCase();
  const atRisk   = stockData.filter(r => r.StockStatus === 'NEARLY_OUT_OF_STOCK');
  const critical = atRisk.filter(r => r.RiskReason === 'BOTH');
  const sufficient = stockData.filter(r => r.StockStatus === 'SUFFICIENT');

  // ── Specific material lookup ─────────────────────────────────────────────
  // Extracts ALL material IDs (pattern MAT-XXXX) mentioned in the message.
  // Handles comma/and-separated lists: "MAT-2001, MAT-3003" or "MAT-2001 and MAT-3003"
  const allMaterialIds = [...new Set(
    (message.match(/\b([A-Za-z]+-[0-9]{3,})\b/gi) || []).map(id => id.toUpperCase())
  )];

  if (allMaterialIds.length > 0) {
    const results = [];
    const notFound = [];

    for (const token of allMaterialIds) {
      let matches = stockData.filter(r => r.Material === token);
      if (!matches.length) {
        matches = stockData.filter(r => r.Material.startsWith(token));
      }
      if (matches.length === 0) {
        notFound.push(token);
      } else if (matches.length === 1) {
        const m = matches[0];
        const icon = m.StockStatus === 'SUFFICIENT' ? '✅' : '⚠️';
        const riskLine = m.RiskDescription
          ? `\n- Risk Reason: ${m.RiskDescription}`
          : '';
        results.push(
          `${icon} **Material ${m.Material}** — ${m.MaterialDescription || 'No description'}\n\n` +
          `- Plant: ${m.Plant} | Storage Location: ${m.StorageLocation}\n` +
          `- Stock Quantity: **${m.StockQuantity} ${m.BaseUnit}**\n` +
          `- Reorder Point: ${m.ReorderPoint} | Safety Stock: ${m.SafetyStock}\n` +
          `- Status: **${m.StockStatus.replace(/_/g, ' ')}**${riskLine}`
        );
      } else {
        const lines = matches.map(m =>
          `- **${m.Material}** (${m.MaterialDescription}) — Plant ${m.Plant} / ${m.StorageLocation} | ` +
          `Stock: ${m.StockQuantity} ${m.BaseUnit} | Status: ${m.StockStatus.replace(/_/g, ' ')}`
        );
        results.push(`**Materials matching "${token}" (${matches.length})**\n\n${lines.join('\n')}`);
      }
    }

    if (notFound.length) {
      results.push(`⚠️ No stock record found for: ${notFound.join(', ')}`);
    }

    // Return combined results only when at least one material was found or explicitly not found
    if (results.length > 0) {
      return results.join('\n\n---\n\n');
    }
    // No matches at all — fall through to generic handlers
  }

  // ── Summary question ─────────────────────────────────────────────────────
  if (/summ|overview|status|how many/.test(q)) {
    return (
      `**Stock Health Summary**\n\n` +
      `- Total materials tracked: ${stockData.length}\n` +
      `- ✅ Sufficient stock: ${sufficient.length}\n` +
      `- ⚠️ Nearly out of stock: ${atRisk.length}\n` +
      `  - 🔴 Critical (both thresholds breached): ${critical.length}\n` +
      `  - 🟠 Below reorder point: ${atRisk.filter(r => r.RiskReason === 'REORDER_POINT_BREACH').length}\n` +
      `  - 🟡 Below safety stock %: ${atRisk.filter(r => r.RiskReason === 'SAFETY_STOCK_PCT_BREACH').length}`
    );
  }

  // ── Critical / urgent / most important ───────────────────────────────────
  if (/critical|urgent|most|priorit|worst/.test(q)) {
    if (!critical.length && !atRisk.length) return 'No critical stock issues found at this time.';
    const top = (critical.length ? critical : atRisk).slice(0, 5);
    const lines = top.map(m =>
      `- **${m.Material}** (${m.MaterialDescription}) — Plant ${m.Plant} / ${m.StorageLocation} | ` +
      `Stock: ${m.StockQuantity} ${m.BaseUnit} | Reorder Point: ${m.ReorderPoint}`
    );
    return `**Most Critical Materials to Reorder**\n\n${lines.join('\n')}`;
  }

  // ── Reorder / what to order ───────────────────────────────────────────────
  if (/reorder|order|buy|replenish|purchas/.test(q)) {
    if (!atRisk.length) return 'No materials require reordering at this time.';
    const lines = atRisk.map(m =>
      `- **${m.Material}** (${m.MaterialDescription}) — Plant ${m.Plant} / ${m.StorageLocation} | ` +
      `Current: ${m.StockQuantity} ${m.BaseUnit} | Reorder at: ${m.ReorderPoint}`
    );
    return (
      `**Materials Recommended for Reordering (${atRisk.length})**\n\n${lines.join('\n')}\n\n` +
      `💡 Prioritize the ${critical.length} critical item(s) marked with both threshold breaches.`
    );
  }

  // ── Plant-specific question ───────────────────────────────────────────────
  const plantMatch = q.match(/plant\s+(\w+)/i);
  if (plantMatch) {
    const plant = plantMatch[1].toUpperCase();
    const plantItems = stockData.filter(r => r.Plant === plant);
    if (!plantItems.length) return `No materials found for plant ${plant}.`;
    const plantRisk = plantItems.filter(r => r.StockStatus === 'NEARLY_OUT_OF_STOCK');
    if (!plantRisk.length) return `✅ All ${plantItems.length} materials in plant ${plant} have sufficient stock.`;
    const lines = plantRisk.map(m =>
      `- **${m.Material}** (${m.MaterialDescription}) — ${m.StorageLocation} | ` +
      `Stock: ${m.StockQuantity} ${m.BaseUnit} | Status: ${m.StockStatus.replace(/_/g, ' ')}`
    );
    return `**At-Risk Materials in Plant ${plant} (${plantRisk.length} / ${plantItems.length} total)**\n\n${lines.join('\n')}`;
  }

  // ── Storage location question ─────────────────────────────────────────────
  const slMatch = q.match(/(?:storage\s+location|sloc|loc(?:ation)?)\s+(\w+)/i);
  if (slMatch) {
    const sloc = slMatch[1].toUpperCase();
    const slocItems = stockData.filter(r => r.StorageLocation === sloc);
    if (!slocItems.length) return `No materials found for storage location ${sloc}.`;
    const lines = slocItems.map(m =>
      `- **${m.Material}** (${m.MaterialDescription}) — Plant ${m.Plant} | ` +
      `Stock: ${m.StockQuantity} ${m.BaseUnit} | Status: ${m.StockStatus.replace(/_/g, ' ')}`
    );
    return `**Materials in Storage Location ${sloc} (${slocItems.length})**\n\n${lines.join('\n')}`;
  }

  // ── Default: at-risk overview ─────────────────────────────────────────────
  if (!atRisk.length) {
    return '✅ All materials currently have sufficient stock. No immediate action required.';
  }
  const topLines = atRisk.slice(0, 8).map(m =>
    `- **${m.Material}** (${m.MaterialDescription}) — Plant ${m.Plant}, ${m.StorageLocation}`
  );
  return (
    `**Stock Recommendations**\n\n` +
    `There are currently **${atRisk.length} material(s)** requiring attention:\n\n` +
    topLines.join('\n') +
    (atRisk.length > 8 ? `\n…and ${atRisk.length - 8} more.` : '') +
    `\n\n💡 **Tip:** Ask about a specific material (e.g. "What about MAT-1007?"), a plant ("Plant 1000"), or say "What should I reorder today?"`
  );
}

/**
 * Apply OData $filter to in-memory classified stock data.
 * Supports equality filters on any string field (e.g. Material, StockStatus, Plant).
 * CQN 'where' array shape: [{ ref: ['FieldName'] }, '=', { val: 'VALUE' }]
 */
function applyFilter(data, where) {
  if (!Array.isArray(where) || where.length === 0) return data;
  try {
    // Handle AND-combined conditions: [cond, 'and', cond, 'and', cond, ...]
    if (where.some(el => el === 'and')) {
      // Split on 'and' and recursively apply each condition
      const conditions = [];
      let current = [];
      for (const el of where) {
        if (el === 'and') {
          conditions.push(current);
          current = [];
        } else {
          current.push(el);
        }
      }
      if (current.length) conditions.push(current);
      return conditions.reduce((acc, cond) => applyFilter(acc, cond), data);
    }

    // Single equality condition: [{ ref: ['Field'] }, '=', { val: 'VALUE' }]
    const [left, op, right] = where;
    const field = left?.ref?.[0];
    const value = right?.val;
    if (field && (op === '=' || op === 'eq') && value !== undefined) {
      return data.filter(r => String(r[field] ?? '') === String(value));
    }
  } catch {
    // ignore filter parse errors — return unfiltered data
  }
  return data;
}
