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
  XCircle
} from 'lucide-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://localhost:8000';

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

// --- Other Tabs (Placeholders) ---
const TimelineTab = () => (
  <div className="neo-card p-8">
    <h2 className="text-3xl font-black uppercase mb-4">Activity Timeline</h2>
    <p className="font-medium">Your captured activity will appear here.</p>
  </div>
);

const SearchTab = () => (
  <div className="max-w-2xl mx-auto space-y-6">
    <div className="neo-card neo-blue p-8">
      <h2 className="text-3xl font-black uppercase mb-6">Search Everything</h2>
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Type your query..."
          className="neo-input flex-1 px-4 py-3 text-lg"
        />
        <button className="neo-button px-6 py-3">
          SEARCH
        </button>
      </div>
    </div>
  </div>
);

const EntitiesTab = () => (
  <div className="neo-card neo-green p-8">
    <h2 className="text-3xl font-black uppercase mb-4">Knowledge Base</h2>
    <p className="font-medium">Extracted entities and concepts.</p>
  </div>
);

const GraphTab = () => (
  <div className="neo-card neo-orange p-8">
    <h2 className="text-3xl font-black uppercase mb-4">Relationship Graph</h2>
    <p className="font-medium">Visual connections between your data.</p>
  </div>
);

export default App;
