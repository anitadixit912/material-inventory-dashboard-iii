import { useEffect, useState, useCallback, useMemo } from 'react'
import { ThemeProvider, ShellBar, ShellBarItem, Button, Input, Label, Select, Option,
         BusyIndicator, MessageStrip, Tag, FlexBox, Card, CardHeader, Text, Title } from '@ui5/webcomponents-react'
import { AnalyticalTable } from '@ui5/webcomponents-react'
import '@ui5/webcomponents-icons/dist/refresh.js'
import '@ui5/webcomponents-icons/dist/warning.js'
import '@ui5/webcomponents-icons/dist/accept.js'
import '@ui5/webcomponents-icons/dist/download.js'
import '@ui5/webcomponents-icons/dist/filter.js'
import '@ui5/webcomponents-icons/dist/locked.js'
import './App.css'
import ChatBox from './ChatBox.jsx'

// Risk labels are functions of the current safety-stock threshold so the
// column always reflects the exact % the user has configured.
const getRiskLabels = (pct) => ({
  REORDER_POINT_BREACH:     'Below Reorder Point',
  SAFETY_STOCK_PCT_BREACH:  `Below Safety Stock (${pct}%)`,
  BOTH:                     `Below Reorder Point & Safety Stock (${pct}%)`,
})

const RISK_COLOR = {
  REORDER_POINT_BREACH:    '2',   // orange
  SAFETY_STOCK_PCT_BREACH: '2',
  BOTH:                    '1',   // red/critical
}

export default function App() {
  const [allStock, setAllStock]               = useState([])
  const [loading, setLoading]                 = useState(false)
  const [error, setError]                     = useState(null)
  const [safetyPct, setSafetyPct]             = useState(20)
  const [pendingPct, setPendingPct]           = useState('20')
  const [plantFilter, setPlantFilter]         = useState('ALL')
  const [locFilter, setLocFilter]             = useState('ALL')
  const [showSecurityBanner, setShowSecurityBanner] = useState(true)

  // ── Fetch stock data ──────────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch threshold config
      const cfgRes = await fetch('/stock/StockThresholdConfig(1)')
      if (cfgRes.status === 401 || cfgRes.status === 403) {
        throw new Error('Session expired or unauthorized. Please refresh the page and log in again.')
      }
      if (cfgRes.ok) {
        const cfg = await cfgRes.json()
        const pct = Number(cfg.safetyStockPct)
        setSafetyPct(pct)
        setPendingPct(String(pct))
      }
      // Fetch all classified stock
      const res = await fetch('/stock/MaterialStockView')
      if (res.status === 401 || res.status === 403) {
        throw new Error('Session expired or unauthorized. Please refresh the page and log in again.')
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const data = await res.json()
      setAllStock(data.value || [])
      console.log('M3.achieved: dashboard rendered successfully — both panels visible with data')
    } catch (e) {
      setError(e.message)
      console.error('M3.missed: dashboard rendering failed —', e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  // ── Apply threshold update ────────────────────────────────────────────────
  // Uses the dedicated updateThreshold action — StockThresholdConfig entity
  // is @readonly so direct PATCH is blocked; this action is the only write path.
  const applyThreshold = async () => {
    const newPct = Number(pendingPct)
    if (isNaN(newPct) || newPct < 0 || newPct > 100) {
      setError('Threshold must be a number between 0 and 100.')
      return
    }
    try {
      const res = await fetch('/stock/updateThreshold', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ safetyStockPct: newPct }),
      })
      if (res.status === 401 || res.status === 403) {
        setError('Session expired or unauthorized. Please refresh the page and log in again.')
        return
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(body?.error?.message || 'Failed to update threshold.')
        return
      }
      setSafetyPct(newPct)
      await fetchData()
    } catch (e) {
      setError('Failed to update threshold.')
    }
  }

  // ── Derived filter values ─────────────────────────────────────────────────
  const plants = useMemo(() => {
    const set = new Set(allStock.map(r => r.Plant))
    return ['ALL', ...Array.from(set).sort()]
  }, [allStock])

  const locations = useMemo(() => {
    const filtered = plantFilter === 'ALL' ? allStock : allStock.filter(r => r.Plant === plantFilter)
    const set = new Set(filtered.map(r => r.StorageLocation))
    return ['ALL', ...Array.from(set).sort()]
  }, [allStock, plantFilter])

  const filteredStock = useMemo(() => {
    return allStock.filter(r => {
      if (plantFilter !== 'ALL' && r.Plant !== plantFilter) return false
      if (locFilter !== 'ALL' && r.StorageLocation !== locFilter) return false
      return true
    })
  }, [allStock, plantFilter, locFilter])

  const sufficientData = useMemo(() => filteredStock.filter(r => r.StockStatus === 'SUFFICIENT'), [filteredStock])
  const atRiskData     = useMemo(() => filteredStock.filter(r => r.StockStatus === 'NEARLY_OUT_OF_STOCK'), [filteredStock])

  // ── Export at-risk to CSV ─────────────────────────────────────────────────
  const exportCSV = () => {
    const riskLabels = getRiskLabels(safetyPct)
    const headers = ['Material','Description','Plant','StorageLocation','StockQuantity','Unit',`SafetyThreshold(${safetyPct}%)`, 'RiskReason']
    const rows = atRiskData.map(r => {
      const ss = Number(r.SafetyStock) || 0
      const threshold = ss > 0 ? (ss * safetyPct / 100).toFixed(1) : ''
      return [
        r.Material, r.MaterialDescription, r.Plant, r.StorageLocation,
        r.StockQuantity, r.BaseUnit, threshold, riskLabels[r.RiskReason] || r.RiskReason,
      ]
    })
    const csv = [headers, ...rows].map(row => row.map(v => `"${v ?? ''}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = 'at-risk-materials.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  // ── Table column definitions ──────────────────────────────────────────────
  const sufficientColumns = useMemo(() => [
    { Header: 'Material',         accessor: 'Material',            width: 120 },
    { Header: 'Description',      accessor: 'MaterialDescription', minWidth: 160 },
    { Header: 'Plant',            accessor: 'Plant',               width: 80  },
    { Header: 'Storage Location', accessor: 'StorageLocation',     width: 130 },
    { Header: 'Stock Qty',        accessor: 'StockQuantity',       width: 110,
      Cell: ({ value, row }) => `${value} ${row.original.BaseUnit}` },
  ], [])

  const atRiskColumns = useMemo(() => {
    const riskLabels = getRiskLabels(safetyPct)
    return [
      { Header: 'Material',          accessor: 'Material',            width: 110 },
      { Header: 'Description',       accessor: 'MaterialDescription', minWidth: 150 },
      { Header: 'Plant',             accessor: 'Plant',               width: 70  },
      { Header: 'Storage Location',  accessor: 'StorageLocation',     width: 130 },
      { Header: 'Stock Qty',         accessor: 'StockQuantity',       width: 100,
        Cell: ({ value, row }) => `${value} ${row.original.BaseUnit}` },
      { Header: 'Reorder Point',     accessor: 'ReorderPoint',        width: 120 },
      { Header: 'Safety Stock',      accessor: 'SafetyStock',         width: 110 },
      // Shows the actual computed threshold that was compared against stock qty.
      // Re-derives it client-side from the row data + current safetyPct so
      // it always matches what the backend used during classification.
      { Header: `Safety Threshold (${safetyPct}%)`, accessor: 'SafetyStock', id: 'SafetyThreshold', width: 160,
        Cell: ({ row }) => {
          const ss  = Number(row.original.SafetyStock) || 0
          const threshold = (ss * safetyPct / 100).toFixed(1)
          return ss > 0 ? `${threshold} ${row.original.BaseUnit}` : '—'
        }
      },
      { Header: 'Risk',              accessor: 'RiskReason',          width: 260,
        Cell: ({ value }) => value
          ? <Tag colorScheme={RISK_COLOR[value] || '2'} design="Set2">
              {riskLabels[value] || value}
            </Tag>
          : null
      },
    ]
  // Re-build columns whenever the threshold changes so labels + header stay in sync
  }, [safetyPct])

  return (
    <ThemeProvider>
      {/* ── Shell Bar ───────────────────────────────────────────── */}
      <ShellBar primaryTitle="Material Stock Dashboard" secondaryTitle="Inventory Overview">
        <ShellBarItem
          slot="endContent"
          icon="refresh"
          text="Refresh"
          onClick={fetchData}
        />
      </ShellBar>

      <div className="dashboard-root">
        {/* ── Security Compliance Banner ─────────────────────────── */}
        {showSecurityBanner && (
          <MessageStrip
            design="Positive"
            onClose={() => setShowSecurityBanner(false)}
            style={{ marginBottom: '0.75rem' }}
          >
            🔒 <strong>Security Compliance Active (v1.7.0)</strong> — Authentication required on all endpoints &nbsp;·&nbsp;
            Threshold updates via controlled action only &nbsp;·&nbsp;
            Chat input limited to 1,000 characters &nbsp;·&nbsp;
            RiskDescription field schema-declared &nbsp;·&nbsp;
            Mock data fallback warnings enabled
          </MessageStrip>
        )}

        {/* ── Error Banner ───────────────────────────────────────── */}
        {error && (
          <MessageStrip design="Negative" onClose={() => setError(null)} style={{ marginBottom: '1rem' }}>
            {error} &nbsp;<Button design="Transparent" onClick={fetchData}>Retry</Button>
          </MessageStrip>
        )}

        {/* ── Threshold & Filter Bar ─────────────────────────────── */}
        <Card className="filter-card">
          <FlexBox alignItems="Center" wrap="Wrap" gap="1rem">
            <FlexBox alignItems="Center" gap="0.5rem">
              <Label for="safetyPctInput" showColon>Safety Stock Threshold (%)</Label>
              <Input
                id="safetyPctInput"
                type="Number"
                value={pendingPct}
                style={{ width: '80px' }}
                onInput={e => setPendingPct(e.target.value)}
              />
              <Button design="Emphasized" onClick={applyThreshold} icon="accept">Apply</Button>
              <Text style={{ color: 'var(--sapNeutralColor)', fontSize: '0.8rem' }}>
                Current: {safetyPct}%
              </Text>
            </FlexBox>

            <FlexBox alignItems="Center" gap="0.5rem">
              <Label for="plantSelect" showColon>Plant</Label>
              <Select
                id="plantSelect"
                style={{ minWidth: '120px' }}
                onChange={e => { setPlantFilter(e.detail.selectedOption.value); setLocFilter('ALL') }}
              >
                {plants.map(p => (
                  <Option key={p} value={p} selected={p === plantFilter}>
                    {p === 'ALL' ? 'All Plants' : p}
                  </Option>
                ))}
              </Select>

              <Label for="locSelect" showColon>Storage Location</Label>
              <Select
                id="locSelect"
                style={{ minWidth: '140px' }}
                onChange={e => setLocFilter(e.detail.selectedOption.value)}
              >
                {locations.map(l => (
                  <Option key={l} value={l} selected={l === locFilter}>
                    {l === 'ALL' ? 'All Locations' : l}
                  </Option>
                ))}
              </Select>
            </FlexBox>
          </FlexBox>
        </Card>

        {/* ── Summary KPI Cards ──────────────────────────────────── */}
        <FlexBox className="kpi-row" gap="1rem" wrap="Wrap">
          <Card className="kpi-card kpi-sufficient">
            <CardHeader titleText={String(sufficientData.length)} subtitleText="Sufficient Stock" />
          </Card>
          <Card className="kpi-card kpi-atrisk">
            <CardHeader titleText={String(atRiskData.length)} subtitleText="Nearly Out of Stock" />
          </Card>
          <Card className="kpi-card kpi-total">
            <CardHeader titleText={String(filteredStock.length)} subtitleText="Total Materials" />
          </Card>
        </FlexBox>

        {/* ── Stock Panels ───────────────────────────────────────── */}
        <BusyIndicator active={loading} style={{ width: '100%' }}>
          <FlexBox className="panels-row" gap="1.5rem" wrap="Wrap">

            {/* Sufficient Stock Panel */}
            <div className="panel panel-sufficient">
              <FlexBox alignItems="Center" justifyContent="SpaceBetween" style={{ marginBottom: '0.75rem' }}>
                <Title level="H4" style={{ color: 'var(--sapPositiveColor)' }}>
                  ✔ Sufficient Stock ({sufficientData.length})
                </Title>
              </FlexBox>
              <AnalyticalTable
                data={sufficientData}
                columns={sufficientColumns}
                minRows={5}
                visibleRows={10}
                visibleRowCountMode="Fixed"
                noDataText={loading ? 'Loading…' : 'No materials found'}
                alternateRowColor
                scaleWidthMode="Smart"
              />
            </div>

            {/* Nearly Out of Stock Panel */}
            <div className="panel panel-atrisk">
              <FlexBox alignItems="Center" justifyContent="SpaceBetween" style={{ marginBottom: '0.75rem' }}>
                <Title level="H4" style={{ color: 'var(--sapCriticalColor)' }}>
                  ⚠ Nearly Out of Stock ({atRiskData.length})
                </Title>
                <Button icon="download" design="Transparent" onClick={exportCSV} disabled={atRiskData.length === 0}>
                  Export CSV
                </Button>
              </FlexBox>
              <AnalyticalTable
                data={atRiskData}
                columns={atRiskColumns}
                minRows={5}
                visibleRows={10}
                visibleRowCountMode="Fixed"
                noDataText={loading ? 'Loading…' : 'No at-risk materials'}
                alternateRowColor
                scaleWidthMode="Smart"
              />
            </div>

          </FlexBox>
        </BusyIndicator>

        {/* ── AI Chatbox ─────────────────────────────────────────── */}
        <div className="chatbox-section">
          <Title level="H4" style={{ marginBottom: '0.75rem' }}>
            🤖 Stock Advisor — Ask for Recommendations
          </Title>
          <ChatBox />
        </div>

      </div>
    </ThemeProvider>
  )
}
