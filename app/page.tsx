'use client';

import { type SubmitEvent, useCallback, useEffect, useState } from 'react';
import {
  ArrowUp, Check, ChevronRight, Circle, Clock3, Code2, Database,
  GitBranch, PanelLeft, Play, Search, ShieldCheck, Sparkles, TableProperties,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type TraceStep = {
  id: number;
  title: string;
  detail: string;
  duration_ms: number;
  tool: string;
  status: 'complete' | 'running';
};

type Investigation = {
  question: string;
  answer: string;
  evidence: Array<Record<string, string | number>>;
  columns: string[];
  trace: TraceStep[];
  mode: string;
};

const sampleResult: Investigation = {
  question: 'Which product category drove the largest revenue growth last quarter?',
  answer:
    'Enterprise Analytics drove the largest quarter-over-quarter revenue growth. Revenue increased by $428,400 (+31.2%), contributing 46% of total company growth. The lift was concentrated in the Northeast and West regions, led by annual plan renewals.',
  columns: ['category', 'q2_revenue', 'q3_revenue', 'growth', 'growth_pct'],
  evidence: [
    { category: 'Enterprise Analytics', q2_revenue: '$1.37M', q3_revenue: '$1.80M', growth: '+$428.4K', growth_pct: '+31.2%' },
    { category: 'Workflow Automation', q2_revenue: '$1.12M', q3_revenue: '$1.31M', growth: '+$189.7K', growth_pct: '+17.0%' },
    { category: 'Data Connectors', q2_revenue: '$0.84M', q3_revenue: '$0.91M', growth: '+$74.2K', growth_pct: '+8.8%' },
  ],
  trace: [
    { id: 1, title: 'Inspected database schema', detail: 'Found 5 tables and 3 relevant relationships', duration_ms: 43, tool: 'inspect_schema', status: 'complete' },
    { id: 2, title: 'Compared quarterly revenue', detail: 'Grouped 18,420 order lines by product category', duration_ms: 112, tool: 'execute_sql', status: 'complete' },
    { id: 3, title: 'Validated regional concentration', detail: 'Cross-checked growth across 4 sales regions', duration_ms: 76, tool: 'analyze_results', status: 'complete' },
    { id: 4, title: 'Synthesized evidence', detail: 'Linked 3 supporting observations to the answer', duration_ms: 28, tool: 'generate_answer', status: 'complete' },
  ],
  mode: 'demo',
};

const suggestions = [
  'Which region has the highest average order value?',
  'What changed in churn over the last 90 days?',
  'Find unusual refund patterns by product.',
];

function formatValue(value: string | number) {
  return typeof value === 'number'
    ? new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)
    : value;
}

export default function Home() {
  const [question, setQuestion] = useState(sampleResult.question);
  const [result, setResult] = useState<Investigation>(sampleResult);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('Sample dataset · 18,420 order lines');

  const investigate = useCallback(async (nextQuestion: string) => {
    const trimmed = nextQuestion.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setNotice('Agent is investigating…');
    try {
      const response = await fetch(`${API_URL}/api/investigations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed }),
      });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const payload = (await response.json()) as Investigation;
      setResult(payload);
      setNotice(`${payload.mode === 'openai' ? 'OpenAI' : 'Demo'} mode · investigation complete`);
    } catch {
      setResult({
        question: trimmed,
        answer:
          'This investigation could not be completed, so there is no evidence to show. Check that the backend is reachable and try again.',
        columns: [],
        evidence: [],
        trace: [],
        mode: 'demo',
      });
      setNotice('Investigation could not be completed · no evidence retrieved');
    } finally {
      setBusy(false);
    }
  }, [busy]);

  useEffect(() => {
    const context = typeof document === 'undefined' ? undefined : document.modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    void Promise.resolve(context.registerTool({
      name: 'start_data_investigation',
      title: 'Start data investigation',
      description: 'Run a read-only investigation for a natural-language business question and update the visible evidence.',
      inputSchema: {
        type: 'object',
        properties: { question: { type: 'string', minLength: 1, maxLength: 1000 } },
        required: ['question'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      async execute(input: unknown) {
        if (!input || typeof input !== 'object' || typeof (input as { question?: unknown }).question !== 'string') {
          throw new Error('question must be a non-empty string');
        }
        const nextQuestion = (input as { question: string }).question.trim();
        if (!nextQuestion) throw new Error('question must be a non-empty string');
        setQuestion(nextQuestion);
        await investigate(nextQuestion);
        return { status: 'complete', question: nextQuestion };
      },
    }, { signal: lifecycle.signal })).catch(() => undefined);
    return () => lifecycle.abort();
  }, [investigate]);

  function onSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    void investigate(question);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark"><GitBranch aria-hidden="true" /></div>
          <div><strong>Tracework</strong><span>Data investigation agent</span></div>
        </div>
        <div className="topbar-actions">
          <Badge variant="outline" className="status-badge"><span className="status-dot" />SQLite connected</Badge>
          <Button variant="outline" size="sm"><Code2 data-icon="inline-start" /> API docs</Button>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className="sidebar">
          <div className="sidebar-heading"><span>Workspace</span><PanelLeft size={15} /></div>
          <nav aria-label="Workspace navigation">
            <a className="nav-item active" href="#investigate"><Search />Investigate</a>
            <a className="nav-item" href="#evidence"><TableProperties />Evidence</a>
            <a className="nav-item" href="#trace"><GitBranch />Execution trace</a>
          </nav>
          <div className="database-card">
            <div className="database-icon"><Database /></div>
            <div><strong>commerce.db</strong><span>5 tables · read only</span></div>
            <ChevronRight size={16} />
          </div>
          <div className="guardrail-note">
            <ShieldCheck />
            <div><strong>Query guard active</strong><p>Only one bounded SELECT statement can run per tool call.</p></div>
          </div>
          <div className="sidebar-footer">
            <span>Environment</span>
            <strong><Circle fill="currentColor" /> Development</strong>
          </div>
        </aside>

        <section className="investigation" id="investigate">
          <div className="eyebrow"><Sparkles /> AI analyst workspace</div>
          <h1>Ask the data.<br /><span>Follow the evidence.</span></h1>
          <p className="lede">Investigate business questions across your relational data. Every answer includes the queries, observations, and sources behind it.</p>

          <form className="question-box" onSubmit={onSubmit}>
            <label htmlFor="question">Business question</label>
            <Textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} rows={3} maxLength={1000} placeholder="Ask a question about revenue, customers, products…" />
            <div className="question-footer">
              <span>{notice}</span>
              <Button type="submit" size="lg" disabled={busy || !question.trim()}>
                {busy ? <Clock3 className="animate-spin" /> : <ArrowUp />}
                {busy ? 'Investigating' : 'Investigate'}
              </Button>
            </div>
          </form>

          <div className="suggestions" aria-label="Suggested questions">
            {suggestions.map((suggestion) => (
              <button key={suggestion} type="button" onClick={() => { setQuestion(suggestion); void investigate(suggestion); }}>
                {suggestion}<ChevronRight />
              </button>
            ))}
          </div>

          <section className="answer-card" aria-live="polite">
            <div className="answer-header">
              <div><span className="section-kicker">Conclusion</span><h2>{result.question}</h2></div>
              {result.evidence.length > 0 && <Badge className="confidence"><Check /> Evidence checked</Badge>}
            </div>
            <p className="answer-copy">{result.answer}</p>
            <div className="answer-meta"><span><Database /> {result.evidence.length} evidence rows</span><span><Clock3 /> {result.trace.reduce((sum, step) => sum + step.duration_ms, 0)} ms tool time</span></div>
          </section>

          <section className="evidence-card" id="evidence">
            <div className="section-title"><div><span className="section-kicker">Supporting data</span><h2>Evidence</h2></div><Badge variant="secondary">Query result</Badge></div>
            <div className="table-wrap">
              <table>
                <thead><tr>{result.columns.map((column) => <th key={column}>{column.replaceAll('_', ' ')}</th>)}</tr></thead>
                <tbody>{result.evidence.map((row, index) => <tr key={index}>{result.columns.map((column) => <td key={column}>{formatValue(row[column] ?? '—')}</td>)}</tr>)}</tbody>
              </table>
            </div>
          </section>
        </section>

        <aside className="trace-panel" id="trace">
          <div className="trace-heading"><div><span className="section-kicker">Agent activity</span><h2>Execution trace</h2></div><Badge variant="outline">{result.trace.length} steps</Badge></div>
          <div className="trace-summary"><Play fill="currentColor" /><div><strong>Investigation complete</strong><span>{result.mode === 'openai' ? 'Live agent' : 'Deterministic demo agent'}</span></div></div>
          <ol className="trace-list">
            {result.trace.map((step, index) => (
              <li key={step.id}>
                <div className="trace-line"><span className="step-number">{step.id}</span>{index < result.trace.length - 1 && <i />}</div>
                <div className="trace-content">
                  <div className="trace-title"><strong>{step.title}</strong><span>{step.duration_ms}ms</span></div>
                  <p>{step.detail}</p><code>{step.tool}</code>
                </div>
              </li>
            ))}
          </ol>
          <div className="trace-footer"><ShieldCheck /><span><strong>Safe execution</strong>All queries validated and limited to 200 rows.</span></div>
        </aside>
      </div>
    </main>
  );
}
