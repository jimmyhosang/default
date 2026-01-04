import React, { useState, useEffect } from 'react';
import {
  Activity,
  Search,
  Database,
  Share2,
  Clock,
  Monitor,
  Clipboard
} from 'lucide-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

// Types
interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
}

const API_BASE = 'http://localhost:8000'; // Adjust for production build

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

  return (
    <div className="min-h-screen w-full bg-slate-50 text-slate-900 font-sans">
      {/* Header */}
      <header className="fixed top-0 left-0 w-full h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 z-50 flex items-center justify-between px-6 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">
            AI
          </div>
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-violet-600">
            Unified AI System
          </h1>
        </div>
        <div className="flex gap-4 text-sm font-medium text-slate-600">
          <TabButton id="overview" label="Overview" icon={<Activity size={16} />} active={activeTab} onClick={setActiveTab} />
          <TabButton id="timeline" label="Timeline" icon={<Clock size={16} />} active={activeTab} onClick={setActiveTab} />
          <TabButton id="search" label="Search" icon={<Search size={16} />} active={activeTab} onClick={setActiveTab} />
          <TabButton id="entities" label="Knowledge" icon={<Database size={16} />} active={activeTab} onClick={setActiveTab} />
          <TabButton id="relationships" label="Graph" icon={<Share2 size={16} />} active={activeTab} onClick={setActiveTab} />
        </div>
        <div className="w-8"></div> {/* Spacer */}
      </header>

      {/* Main Content */}
      <main className="pt-24 px-6 pb-12 max-w-7xl mx-auto">
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <OverviewTab stats={stats} loading={loading} />
            </motion.div>
          )}

          {activeTab === 'timeline' && <TimelineTab key="timeline" />}
          {activeTab === 'search' && <SearchTab key="search" />}
          {activeTab === 'entities' && <EntitiesTab key="entities" />}
          {activeTab === 'relationships' && <GraphTab key="relationships" />}
        </AnimatePresence>
      </main>
    </div>
  );
}

// --- Components ---

const TabButton = ({ id, label, icon, active, onClick }: any) => (
  <button
    onClick={() => onClick(id)}
    className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-all ${active === id
        ? 'bg-blue-100 text-blue-700 shadow-sm'
        : 'hover:bg-slate-100 hover:text-slate-900'
      }`}
  >
    {icon}
    {label}
  </button>
);

const OverviewTab = ({ stats, loading }: any) => {
  if (loading) return <div className="p-10 text-center text-slate-500">Loading insights...</div>;
  if (!stats) return <div className="p-10 text-center text-red-500">Failed to load data</div>;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total Captured"
          value={stats.total_content?.toLocaleString()}
          icon={<Database className="text-blue-500" />}
        />
        <StatCard
          label="Entities Found"
          value={stats.total_entities?.toLocaleString()}
          icon={<Activity className="text-violet-500" />}
        />
        <StatCard
          label="Screen Captures"
          value={stats.by_source?.screen?.toLocaleString()}
          icon={<Monitor className="text-emerald-500" />}
        />
        <StatCard
          label="Clipboard Items"
          value={stats.by_source?.clipboard?.toLocaleString()}
          icon={<Clipboard className="text-amber-500" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-semibold mb-4">System Status</h3>
          <div className="space-y-4">
            <StatusRow label="Vector Database" status={stats.vector_db_available} />
            <StatusRow label="Entity Extraction" status={stats.entity_extraction_available} />
            <StatusRow label="Local LLM (Ollama)" status={true} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
          <div className="h-40 flex items-center justify-center text-slate-400">
            [Activity Chart Visualization]
          </div>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ label, value, icon }: StatCardProps) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
    <div className="flex justify-between items-start mb-4">
      <div className="p-2 bg-slate-50 rounded-lg">{icon}</div>
    </div>
    <div className="text-3xl font-bold text-slate-900 mb-1">{value || 0}</div>
    <div className="text-sm text-slate-500">{label}</div>
  </div>
);

const StatusRow = ({ label, status }: { label: string, status: boolean }) => (
  <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
    <span className="font-medium text-slate-700">{label}</span>
    <span className={`px-2 py-1 rounded text-xs font-medium ${status ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
      }`}>
      {status ? 'Active' : 'Inactive'}
    </span>
  </div>
);

const TimelineTab = () => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
    <h2 className="text-xl font-bold mb-4">Activity Timeline</h2>
    <p className="text-slate-500">Timeline visualization would act here, fetching data from /api/timeline.</p>
  </div>
);

const SearchTab = () => (
  <div className="max-w-3xl mx-auto space-y-6">
    <div className="relative">
      <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
      <input
        type="text"
        placeholder="Search everything (commands, code, documents)..."
        className="w-full pl-12 pr-4 py-4 rounded-xl border border-slate-200 shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-lg"
      />
    </div>
    <div className="text-center text-slate-500 mt-20">
      Enter a query to search across your captured digital history.
    </div>
  </div>
);

const EntitiesTab = () => <div className="text-center p-10">Knowledge Graph View</div>;
const GraphTab = () => <div className="text-center p-10">Relationship Graph View</div>;

export default App;
