import { useState, useEffect } from 'react';
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
  RefreshCw
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
        </AnimatePresence>
      </main>
    </div>
  );
}

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

        <div className="neo-card neo-purple p-6">
          <h3 className="text-xl font-black uppercase mb-4 border-b-4 border-black pb-2">
            Quick Actions
          </h3>
          <div className="space-y-3">
            <button className="neo-button w-full py-3 bg-white">
              🔍 Search Everything
            </button>
            <button className="neo-button w-full py-3 bg-white">
              📸 New Capture
            </button>
            <button className="neo-button w-full py-3 bg-white">
              🤖 Ask AI
            </button>
          </div>
        </div>
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
  const [typeFilter, setTypeFilter] = useState<string>('all');

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
        <div className="neo-card p-12 text-center">
          <div className="text-xl font-bold">NO ENTITIES FOUND</div>
          <p className="mt-2">Entities will be extracted from captured content.</p>
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

const GraphTab = () => (
  <div className="neo-card neo-orange p-8">
    <h2 className="text-3xl font-black uppercase mb-4">Relationship Graph</h2>
    <p className="font-medium">Visual connections between your data.</p>
  </div>
);

export default App;
