import React, { useState, useEffect } from 'react';
import {
  Activity,
  Search,
  Database,
  Share2,
  Clock,
  Monitor,
  Clipboard,
  Zap,
  CheckCircle,
  XCircle,
  FileText,
  User,
  Building,
  Calendar,
  DollarSign,
  Filter,
  RefreshCw,
  Play,
  Square,
  Settings
} from 'lucide-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

// Use relative URLs so API works regardless of localhost vs 127.0.0.1
const API_BASE = '';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/stats`);
      setStats(res.data);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Activity size={18} /> },
    { id: 'timeline', label: 'Timeline', icon: <Clock size={18} /> },
    { id: 'search', label: 'Search', icon: <Search size={18} /> },
    { id: 'entities', label: 'Knowledge', icon: <Database size={18} /> },
    { id: 'graph', label: 'Graph', icon: <Share2 size={18} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={18} /> },
  ];

  return (
    <div className="min-h-screen bg-white p-6">
      {/* Header */}
      <header className="neo-card neo-yellow p-4 mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-black text-white flex items-center justify-center font-black text-xl">
              AI
            </div>
            <h1 className="text-2xl font-black uppercase tracking-tight">
              Unified AI System
            </h1>
          </div>
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`neo-button px-4 py-2 flex items-center gap-2 ${activeTab === tab.id ? 'neo-pink' : 'bg-white'
                  }`}
              >
                {tab.icon}
                <span className="hidden md:inline">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <OverviewTab stats={stats} loading={loading} />
            </motion.div>
          )}
          {activeTab === 'timeline' && <TimelineTab key="timeline" />}
          {activeTab === 'search' && <SearchTab key="search" />}
          {activeTab === 'entities' && <EntitiesTab key="entities" />}
          {activeTab === 'graph' && <GraphTab key="graph" />}
          {activeTab === 'settings' && <SettingsTab key="settings" />}
        </AnimatePresence>
      </main>
    </div>
  );
}

// --- Action Bar Component ---
const ActionBar = () => {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<any>(null);
  const [executing, setExecuting] = useState(false);

  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setExecuting(true);
    setResult(null);

    // Simple parser for demonstration
    // "open_file /path/to/file" -> action: "open_file", params: { path: "/path/to/file" }
    // "search query" -> action: "search", params: { query: "query" }
    // "summarize" -> action: "summarize_today"

    let action = 'search';
    let params: any = { query: input };

    if (input.startsWith('open ')) {
      action = 'open_file';
      params = { path: input.substring(5) };
    } else if (input === 'summarize') {
      action = 'summarize_today';
      params = {};
    }

    try {
      const res = await axios.post(`${API_BASE}/api/actions/execute`, { action, params });
      setResult(res.data);
    } catch (err) {
      console.error(err);
      setResult({ status: 'error', results: ['Failed to execute action'] });
    }
    setExecuting(false);
  };

  return (
    <div className="neo-card p-6 bg-black text-white">
      <h3 className="text-xl font-black uppercase mb-4 text-white">System Actions</h3>
      <form onSubmit={handleExecute} className="flex gap-4">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a command (e.g., 'search project', 'open /path/to/file', 'summarize')..."
          className="flex-1 bg-white text-black p-3 font-mono border-2 border-white focus:outline-none focus:neo-yellow"
        />
        <button
          type="submit"
          disabled={executing}
          className="neo-button neo-yellow px-6 font-bold text-black border-white hover:bg-white disabled:opacity-50"
        >
          {executing ? 'RUNNING...' : 'EXECUTE'}
        </button>
      </form>

      {result && (
        <div className="mt-4 p-4 border-2 border-white bg-gray-900 font-mono text-sm max-h-40 overflow-y-auto">
          <div className="font-bold text-green-400 mb-2">
            &gt; {result.status === 'success' ? 'SUCCESS' : 'ERROR'} ({result.action})
          </div>
          {result.results && result.results.map((line: any, i: number) => (
            <div key={i} className="text-gray-300">
              {typeof line === 'string' ? line : JSON.stringify(line)}
            </div>
          ))}
          {result.results && result.results.length === 0 && (
            <div className="text-gray-500 italic">No output</div>
          )}
        </div>
      )}
    </div>
  );
};

// --- Overview Tab ---
const OverviewTab = ({ stats, loading }: any) => {
  if (loading) {
    return (
      <div className="neo-card p-12 text-center">
        <div className="text-2xl font-bold animate-pulse">LOADING...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="neo-card neo-pink p-12 text-center">
        <div className="text-2xl font-bold">FAILED TO LOAD DATA</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <ActionBar />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Captured"
          value={stats.total_content || 0}
          color="neo-yellow"
          icon={<Database size={24} />}
        />
        <StatCard
          label="Entities Found"
          value={stats.total_entities || 0}
          color="neo-pink"
          icon={<Zap size={24} />}
        />
        <StatCard
          label="Screen Captures"
          value={stats.by_source?.screen || 0}
          color="neo-blue"
          icon={<Monitor size={24} />}
        />
        <StatCard
          label="Clipboard Items"
          value={stats.by_source?.clipboard || 0}
          color="neo-green"
          icon={<Clipboard size={24} />}
        />
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="neo-card p-6">
          <h3 className="text-xl font-black uppercase mb-4 border-b-4 border-black pb-2">
            System Status
          </h3>
          <div className="space-y-3">
            <StatusRow label="Vector Database" status={stats.vector_db_available} />
            <StatusRow label="Entity Extraction" status={stats.entity_extraction_available} />
            <StatusRow label="Local LLM (Ollama)" status={true} />
          </div>
        </div>

        <CaptureControlPanel />
      </div>
    </div>
  );
};

const StatCard = ({ label, value, color, icon }: any) => (
  <div className={`neo-card ${color} p-6`}>
    <div className="flex justify-between items-start mb-4">
      <div className="p-2 bg-white border-2 border-black">{icon}</div>
    </div>
    <div className="text-5xl font-black mb-2">{value.toLocaleString()}</div>
    <div className="text-sm font-bold uppercase tracking-wide">{label}</div>
  </div>
);

const StatusRow = ({ label, status }: { label: string; status: boolean }) => (
  <div className="flex items-center justify-between p-3 bg-white border-2 border-black">
    <span className="font-bold">{label}</span>
    <span className={`flex items-center gap-2 font-bold ${status ? 'text-green-600' : 'text-red-600'}`}>
      {status ? <CheckCircle size={18} /> : <XCircle size={18} />}
      {status ? 'ACTIVE' : 'INACTIVE'}
    </span>
  </div>
);

// --- Capture Control Panel ---
const CaptureControlPanel = () => {
  const [status, setStatus] = useState<any>({});

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/capture/status`);
      setStatus(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const toggleDaemon = async (name: string, isRunning: boolean) => {
    try {
      const action = isRunning ? 'stop' : 'start';
      await axios.post(`${API_BASE}/api/capture/${action}/${name}`);
      await fetchStatus(); // Refresh status
    } catch (err) {
      console.error(err);
    }
  };

  const startAll = async () => {
    await axios.post(`${API_BASE}/api/capture/start-all`);
    await fetchStatus();
  };

  const stopAll = async () => {
    await axios.post(`${API_BASE}/api/capture/stop-all`);
    await fetchStatus();
  };

  const daemons = [
    { id: 'screen', label: 'Screen Capture', icon: <Monitor size={18} /> },
    { id: 'clipboard', label: 'Clipboard Monitor', icon: <Clipboard size={18} /> },
    { id: 'file', label: 'File Watcher', icon: <FileText size={18} /> },
  ];

  return (
    <div className="neo-card neo-purple p-6">
      <h3 className="text-xl font-black uppercase mb-4 border-b-4 border-black pb-2">
        Capture Daemons
      </h3>
      <div className="space-y-3">
        {daemons.map((daemon) => {
          const isRunning = status[daemon.id]?.running;
          return (
            <div
              key={daemon.id}
              className="flex items-center justify-between p-3 bg-white border-2 border-black"
            >
              <div className="flex items-center gap-2">
                {daemon.icon}
                <span className="font-bold">{daemon.label}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold ${isRunning ? 'text-green-600' : 'text-gray-400'}`}>
                  {isRunning ? 'RUNNING' : 'STOPPED'}
                </span>
                <button
                  onClick={() => toggleDaemon(daemon.id, isRunning)}
                  className={`neo-button p-2 ${isRunning ? 'neo-pink' : 'neo-green'}`}
                  title={isRunning ? 'Stop' : 'Start'}
                >
                  {isRunning ? <Square size={14} /> : <Play size={14} />}
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-2 mt-4">
        <button onClick={startAll} className="neo-button flex-1 py-2 neo-green">
          <Play size={14} className="inline mr-1" /> START ALL
        </button>
        <button onClick={stopAll} className="neo-button flex-1 py-2 neo-pink">
          <Square size={14} className="inline mr-1" /> STOP ALL
        </button>
      </div>
    </div>
  );
};

// --- Timeline Tab ---
const TimelineTab = () => {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [days, setDays] = useState(7);

  const fetchTimeline = async () => {
    setLoading(true);
    try {
      const params: any = { days, limit: 100 };
      if (filter !== 'all') params.source_type = filter;
      const res = await axios.get(`${API_BASE}/api/timeline`, { params });
      setItems(res.data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchTimeline(); }, [filter, days]);

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'screen': return <Monitor size={16} />;
      case 'clipboard': return <Clipboard size={16} />;
      case 'file': return <FileText size={16} />;
      default: return <Database size={16} />;
    }
  };

  const getSourceColor = (type: string) => {
    switch (type) {
      case 'screen': return 'neo-blue';
      case 'clipboard': return 'neo-green';
      case 'file': return 'neo-purple';
      default: return 'bg-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="neo-card p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter size={18} />
          <span className="font-bold uppercase text-sm">Source:</span>
        </div>
        {['all', 'screen', 'clipboard', 'file'].map((src) => (
          <button
            key={src}
            onClick={() => setFilter(src)}
            className={`neo-button px-3 py-1 text-sm ${filter === src ? 'neo-yellow' : 'bg-white'}`}
          >
            {src.toUpperCase()}
          </button>
        ))}
        <div className="flex items-center gap-2 ml-auto">
          <span className="font-bold uppercase text-sm">Days:</span>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="neo-input px-2 py-1"
          >
            <option value={1}>1</option>
            <option value={7}>7</option>
            <option value={30}>30</option>
            <option value={90}>90</option>
          </select>
        </div>
        <button onClick={fetchTimeline} className="neo-button p-2">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Timeline Items */}
      {loading ? (
        <div className="neo-card p-12 text-center">
          <div className="text-2xl font-bold animate-pulse">LOADING...</div>
        </div>
      ) : items.length === 0 ? (
        <div className="neo-card p-12 text-center">
          <div className="text-xl font-bold">NO ACTIVITY FOUND</div>
          <p className="mt-2">Run capture daemons to record your activity.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item, i) => (
            <div key={i} className={`neo-card p-4 border-l-4 ${getSourceColor(item.source_type)}`}>
              <div className="flex justify-between items-start mb-2">
                <div className={`flex items-center gap-2 px-2 py-1 ${getSourceColor(item.source_type)} border-2 border-black`}>
                  {getSourceIcon(item.source_type)}
                  <span className="font-bold uppercase text-xs">{item.source_type}</span>
                </div>
                <span className="text-xs font-bold text-gray-500">
                  {new Date(item.timestamp).toLocaleString()}
                </span>
              </div>
              <div className="font-mono text-sm whitespace-pre-wrap break-words">
                {item.content_preview || item.content?.substring(0, 300)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const SearchTab = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await axios.get(`${API_BASE}/api/search`, {
        params: { q: query, mode: 'semantic' }
      });
      setResults(res.data);
    } catch (err) {
      console.error(err);
    }
    setSearching(false);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="neo-card neo-blue p-8">
        <h2 className="text-3xl font-black uppercase mb-6">Search Everything</h2>
        <div className="flex gap-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Ask a question or search keywords..."
            className="neo-input flex-1 px-4 py-3 text-lg"
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            className="neo-button px-6 py-3 disabled:opacity-50"
          >
            {searching ? 'SEARCHING...' : 'SEARCH'}
          </button>
        </div>
      </div>

      {results && (
        <div className="space-y-6">
          {/* AI Answer */}
          {results.answer && (
            <div className="neo-card neo-yellow p-6">
              <div className="flex items-center gap-2 mb-4">
                <Zap size={24} />
                <h3 className="text-xl font-black uppercase">AI Answer</h3>
              </div>
              <div className="text-lg leading-relaxed whitespace-pre-wrap">
                {results.answer}
              </div>
            </div>
          )}

          {/* Results List */}
          <div className="grid gap-4">
            {results.results?.map((item: any, i: number) => (
              <div key={i} className="neo-card p-4 hover:translate-x-1 transition-transform">
                <div className="flex justify-between items-start mb-2">
                  <span className="bg-black text-white text-xs font-bold px-2 py-1 uppercase">
                    {item.source_type}
                  </span>
                  <span className="text-xs font-bold text-gray-500">
                    {new Date(item.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="font-mono text-sm line-clamp-3">
                  {item.content}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// --- Entities Tab ---
const EntitiesTab = () => {
  const [entities, setEntities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [syncMessage, setSyncMessage] = useState<string>('');

  const fetchEntities = async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (typeFilter !== 'all') params.entity_type = typeFilter;
      const res = await axios.get(`${API_BASE}/api/entities`, { params });
      setEntities(res.data.entities || []);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const syncEntities = async () => {
    setSyncing(true);
    setSyncMessage('Syncing captures...');
    try {
      // First sync captures to semantic store
      await axios.post(`${API_BASE}/api/entities/sync`);
      setSyncMessage('Extracting entities...');

      // Then reprocess all entities
      const res = await axios.post(`${API_BASE}/api/entities/reprocess`);
      setSyncMessage(res.data.message || 'Complete!');

      // Refresh entities list
      await fetchEntities();
    } catch (err) {
      console.error(err);
      setSyncMessage('Sync failed');
    }
    setSyncing(false);
  };

  useEffect(() => { fetchEntities(); }, [typeFilter]);

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'person': return <User size={16} />;
      case 'org': return <Building size={16} />;
      case 'date': return <Calendar size={16} />;
      case 'money': return <DollarSign size={16} />;
      default: return <Database size={16} />;
    }
  };

  const getEntityColor = (type: string) => {
    switch (type) {
      case 'person': return 'neo-pink';
      case 'org': return 'neo-blue';
      case 'date': return 'neo-yellow';
      case 'money': return 'neo-green';
      default: return 'neo-purple';
    }
  };

  // Group entities by type
  const groupedEntities = entities.reduce((acc: any, entity) => {
    const type = entity.type || entity.entity_type || 'other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(entity);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="neo-card p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter size={18} />
          <span className="font-bold uppercase text-sm">Entity Type:</span>
        </div>
        {['all', 'person', 'org', 'date', 'money', 'other'].map((type) => (
          <button
            key={type}
            onClick={() => setTypeFilter(type)}
            className={`neo-button px-3 py-1 text-sm ${typeFilter === type ? 'neo-yellow' : 'bg-white'}`}
          >
            {type.toUpperCase()}
          </button>
        ))}
        <button onClick={fetchEntities} className="neo-button p-2 ml-auto">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Entity Cards */}
      {loading ? (
        <div className="neo-card p-12 text-center">
          <div className="text-2xl font-bold animate-pulse">LOADING...</div>
        </div>
      ) : entities.length === 0 ? (
        <div className="neo-card p-12 text-center space-y-4">
          <div className="text-xl font-bold">NO ENTITIES FOUND</div>
          <p className="text-gray-600">Entities like people, organizations, dates, and money will be extracted from your captured content.</p>
          <button
            onClick={syncEntities}
            disabled={syncing}
            className="neo-button neo-green px-6 py-3 text-lg disabled:opacity-50"
          >
            {syncing ? (
              <span className="flex items-center gap-2">
                <RefreshCw size={18} className="animate-spin" />
                {syncMessage}
              </span>
            ) : (
              '🔄 SYNC & EXTRACT ENTITIES'
            )}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.keys(groupedEntities).map((type) => (
            <div key={type} className={`neo-card ${getEntityColor(type)} p-4`}>
              <div className="flex items-center gap-2 mb-4">
                {getEntityIcon(type)}
                <h3 className="font-black uppercase">{type} ({groupedEntities[type].length})</h3>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {groupedEntities[type].slice(0, 10).map((entity: any, i: number) => (
                  <div key={i} className="bg-white border-2 border-black p-2 text-sm font-mono">
                    {entity.text || entity.entity_text}
                  </div>
                ))}
                {groupedEntities[type].length > 10 && (
                  <div className="text-sm font-bold text-center">
                    +{groupedEntities[type].length - 10} more
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// --- Graph Tab ---
const GraphTab = () => {
  const [graphData, setGraphData] = useState<any>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/api/graph`, { params: { limit: 50 } });
      setGraphData(res.data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      const { offsetWidth, offsetHeight } = containerRef.current;
      setDimensions({ width: offsetWidth || 800, height: Math.max(offsetHeight, 500) });
    }
  }, [graphData]);

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'person': return '#ec4899'; // pink
      case 'org': return '#3b82f6'; // blue
      case 'date': return '#eab308'; // yellow
      case 'money': return '#22c55e'; // green
      case 'gpe': return '#f97316'; // orange
      default: return '#8b5cf6'; // purple
    }
  };

  return (
    <div className="space-y-6">
      <div className="neo-card p-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black uppercase">Entity Relationship Graph</h2>
          <p className="text-sm text-gray-600">Entities that appear together in the same content are connected.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm">
            <span className="font-bold">{graphData.stats?.total_nodes || 0}</span> nodes,{' '}
            <span className="font-bold">{graphData.stats?.total_links || 0}</span> connections
          </div>
          <button onClick={fetchGraphData} className="neo-button p-2">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 px-2">
        {[
          { type: 'person', label: 'People', color: '#ec4899' },
          { type: 'org', label: 'Organizations', color: '#3b82f6' },
          { type: 'date', label: 'Dates', color: '#eab308' },
          { type: 'money', label: 'Money', color: '#22c55e' },
          { type: 'gpe', label: 'Places', color: '#f97316' },
          { type: 'other', label: 'Other', color: '#8b5cf6' },
        ].map((item) => (
          <div key={item.type} className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full border-2 border-black" style={{ backgroundColor: item.color }} />
            <span className="text-sm font-bold">{item.label}</span>
          </div>
        ))}
      </div>

      {/* Graph */}
      <div ref={containerRef} className="neo-card p-0 overflow-hidden" style={{ height: '500px' }}>
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-2xl font-bold animate-pulse">LOADING GRAPH...</div>
          </div>
        ) : graphData.nodes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-8">
            <div className="text-xl font-bold mb-2">NO GRAPH DATA</div>
            <p className="text-gray-600 text-center">
              Extract entities first from the Knowledge tab, then return here to see relationships.
            </p>
          </div>
        ) : (
          <ForceGraphComponent
            data={graphData}
            width={dimensions.width}
            height={500}
            getNodeColor={getNodeColor}
            onNodeClick={setSelectedNode}
          />
        )}
      </div>

      {/* Selected Entity Info */}
      {selectedNode && (
        <div className="neo-card neo-yellow p-4">
          <h3 className="font-black uppercase mb-2">Selected Entity</h3>
          <div className="grid grid-cols-3 gap-4">
            <div><span className="text-sm text-gray-600">Name:</span> <span className="font-bold">{selectedNode.label}</span></div>
            <div><span className="text-sm text-gray-600">Type:</span> <span className="font-bold uppercase">{selectedNode.type}</span></div>
            <div><span className="text-sm text-gray-600">Occurrences:</span> <span className="font-bold">{selectedNode.freq}</span></div>
          </div>
        </div>
      )}
    </div>
  );
};

// Force Graph Component using Canvas
const ForceGraphComponent = ({ data, width, height, getNodeColor, onNodeClick }: any) => {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const [nodes, setNodes] = useState<any[]>([]);
  const [links, setLinks] = useState<any[]>([]);

  useEffect(() => {
    // Initialize node positions
    const initializedNodes = data.nodes.map((node: any) => ({
      ...node,
      x: width / 2 + (Math.random() - 0.5) * 300,
      y: height / 2 + (Math.random() - 0.5) * 300,
      vx: 0,
      vy: 0,
    }));
    setNodes(initializedNodes);
    setLinks(data.links);
  }, [data, width, height]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Simple force simulation
    const simulate = () => {
      // Apply forces
      nodes.forEach((node) => {
        // Center gravity
        node.vx += (width / 2 - node.x) * 0.001;
        node.vy += (height / 2 - node.y) * 0.001;

        // Repulsion between nodes
        nodes.forEach((other) => {
          if (node.id !== other.id) {
            const dx = node.x - other.x;
            const dy = node.y - other.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            if (dist < 100) {
              const force = 50 / dist;
              node.vx += (dx / dist) * force;
              node.vy += (dy / dist) * force;
            }
          }
        });
      });

      // Link forces (attraction)
      links.forEach((link: any) => {
        const source = nodes.find((n) => n.id === link.source);
        const target = nodes.find((n) => n.id === link.target);
        if (source && target) {
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (dist - 80) * 0.01;
          source.vx += (dx / dist) * force;
          source.vy += (dy / dist) * force;
          target.vx -= (dx / dist) * force;
          target.vy -= (dy / dist) * force;
        }
      });

      // Update positions
      nodes.forEach((node) => {
        node.vx *= 0.9; // Damping
        node.vy *= 0.9;
        node.x += node.vx;
        node.y += node.vy;
        // Bounds
        node.x = Math.max(20, Math.min(width - 20, node.x));
        node.y = Math.max(20, Math.min(height - 20, node.y));
      });

      // Draw
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, width, height);

      // Draw links
      ctx.strokeStyle = '#00000033';
      ctx.lineWidth = 1;
      links.forEach((link: any) => {
        const source = nodes.find((n) => n.id === link.source);
        const target = nodes.find((n) => n.id === link.target);
        if (source && target) {
          ctx.beginPath();
          ctx.moveTo(source.x, source.y);
          ctx.lineTo(target.x, target.y);
          ctx.stroke();
        }
      });

      // Draw nodes
      nodes.forEach((node) => {
        const radius = node.size / 2;
        ctx.fillStyle = getNodeColor(node.type);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Labels for larger nodes
        if (node.size > 10) {
          ctx.fillStyle = '#000';
          ctx.font = 'bold 10px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(node.label.substring(0, 12), node.x, node.y + radius + 12);
        }
      });
    };

    const interval = setInterval(simulate, 50);
    return () => clearInterval(interval);
  }, [nodes, links, width, height, getNodeColor]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const clicked = nodes.find((node) => {
      const dx = node.x - x;
      const dy = node.y - y;
      return Math.sqrt(dx * dx + dy * dy) < node.size / 2 + 5;
    });

    if (clicked) onNodeClick(clicked);
  };

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onClick={handleClick}
      style={{ cursor: 'pointer' }}
    />
  );
};

// --- Settings Tab ---
const SettingsTab = () => {
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('general');
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/settings`);
      setSettings(res.data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const updateSettings = async (newSettings: any) => {
    try {
      await axios.put(`${API_BASE}/api/settings`, newSettings);
      setSettings((prev: any) => ({ ...prev, ...newSettings }));
      setMessage('Settings saved!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      console.error(err);
      setMessage('Failed to save settings');
    }
  };

  const handleCaptureChange = (key: string, value: any) => {
    updateSettings({ capture: { ...settings.capture, [key]: value } });
  };

  const handleStorageChange = (key: string, value: any) => {
    updateSettings({ storage: { ...settings.storage, [key]: value } });
  };

  const handleLLMChange = (key: string, value: any) => {
    updateSettings({ llm: { ...settings.llm, [key]: value } });
  };

  if (loading || !settings) return <div className="p-8 text-center font-bold">LOADING SETTINGS...</div>;

  return (
    <div className="space-y-6">
      <div className="neo-card p-4 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-black uppercase">System Settings</h2>
          <p className="text-sm text-gray-600">Configure capture, storage, and AI providers.</p>
        </div>
        {message && (
          <div className="neo-card neo-green px-4 py-2 font-bold animate-pulse">
            {message}
          </div>
        )}
      </div>

      <div className="flex gap-4 border-b-2 border-black pb-4 overflow-x-auto">
        {['general', 'storage', 'ai'].map((section) => (
          <button
            key={section}
            onClick={() => setActiveSection(section)}
            className={`neo-button px-4 py-2 uppercase font-bold text-sm ${activeSection === section ? 'neo-yellow' : 'bg-white'
              }`}
          >
            {section}
          </button>
        ))}
      </div>

      {activeSection === 'general' && (
        <div className="neo-card p-6 space-y-6">
          <h3 className="text-xl font-black uppercase mb-4">Capture Settings</h3>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="font-bold">Screen Capture Interval (seconds)</label>
              <input
                type="number"
                value={settings.capture.screen_interval}
                onChange={(e) => handleCaptureChange('screen_interval', parseInt(e.target.value))}
                className="border-2 border-black p-2 w-32 font-mono"
              />
            </div>

            <div className="flex items-center justify-between">
              <label className="font-bold">Enable Clipboard Monitor</label>
              <input
                type="checkbox"
                checked={settings.capture.clipboard_enabled}
                onChange={(e) => handleCaptureChange('clipboard_enabled', e.target.checked)}
                className="w-6 h-6 border-2 border-black accent-black"
              />
            </div>

            <div className="flex items-center justify-between">
              <label className="font-bold">Enable File Watcher</label>
              <input
                type="checkbox"
                checked={settings.capture.file_watch_enabled}
                onChange={(e) => handleCaptureChange('file_watch_enabled', e.target.checked)}
                className="w-6 h-6 border-2 border-black accent-black"
              />
            </div>

            <div>
              <label className="font-bold block mb-2">Watch Directories</label>
              <div className="space-y-2">
                {settings.capture.watch_directories.map((dir: string, i: number) => (
                  <div key={i} className="bg-gray-100 p-2 border-2 border-black font-mono text-sm">
                    {dir}
                  </div>
                ))}
                <p className="text-xs text-gray-500 mt-1">* Edit config file to change directories</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeSection === 'storage' && (
        <div className="neo-card p-6 space-y-6">
          <h3 className="text-xl font-black uppercase mb-4">Storage Limits</h3>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="font-bold">Max Captures to Keep</label>
              <input
                type="number"
                value={settings.storage.max_captures}
                onChange={(e) => handleStorageChange('max_captures', parseInt(e.target.value))}
                className="border-2 border-black p-2 w-32 font-mono"
              />
            </div>

            <div className="flex items-center justify-between">
              <label className="font-bold">Retention Period (Days)</label>
              <input
                type="number"
                value={settings.storage.max_days}
                onChange={(e) => handleStorageChange('max_days', parseInt(e.target.value))}
                className="border-2 border-black p-2 w-32 font-mono"
              />
            </div>

            <div className="flex items-center justify-between">
              <label className="font-bold">Auto-Cleanup Enabled</label>
              <input
                type="checkbox"
                checked={settings.storage.auto_cleanup}
                onChange={(e) => handleStorageChange('auto_cleanup', e.target.checked)}
                className="w-6 h-6 border-2 border-black accent-black"
              />
            </div>
          </div>
        </div>
      )}

      {activeSection === 'ai' && (
        <div className="neo-card p-6 space-y-6">
          <h3 className="text-xl font-black uppercase mb-4">AI Provider Configuration</h3>

          <div className="space-y-4">
            <div>
              <label className="font-bold block mb-2">LLM Provider</label>
              <select
                value={settings.llm.provider}
                onChange={(e) => handleLLMChange('provider', e.target.value)}
                className="w-full border-2 border-black p-2 bg-white font-mono"
              >
                <option value="ollama">Ollama (Local)</option>
                <option value="openai">OpenAI (Cloud)</option>
                <option value="anthropic">Anthropic (Cloud)</option>
              </select>
            </div>

            {settings.llm.provider === 'ollama' && (
              <>
                <div>
                  <label className="font-bold block mb-2">Ollama Model</label>
                  <input
                    type="text"
                    value={settings.llm.ollama_model}
                    onChange={(e) => handleLLMChange('ollama_model', e.target.value)}
                    className="w-full border-2 border-black p-2 font-mono"
                  />
                </div>
                <div>
                  <label className="font-bold block mb-2">Ollama URL</label>
                  <input
                    type="text"
                    value={settings.llm.ollama_url}
                    onChange={(e) => handleLLMChange('ollama_url', e.target.value)}
                    className="w-full border-2 border-black p-2 font-mono"
                  />
                </div>
              </>
            )}

            {settings.llm.provider === 'openai' && (
              <div>
                <label className="font-bold block mb-2">OpenAI API Key</label>
                <input
                  type="password"
                  value={settings.llm.openai_api_key}
                  onChange={(e) => handleLLMChange('openai_api_key', e.target.value)}
                  className="w-full border-2 border-black p-2 font-mono"
                  placeholder="sk-..."
                />
              </div>
            )}

            {settings.llm.provider === 'anthropic' && (
              <div>
                <label className="font-bold block mb-2">Anthropic API Key</label>
                <input
                  type="password"
                  value={settings.llm.anthropic_api_key}
                  onChange={(e) => handleLLMChange('anthropic_api_key', e.target.value)}
                  className="w-full border-2 border-black p-2 font-mono"
                  placeholder="sk-ant-..."
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
