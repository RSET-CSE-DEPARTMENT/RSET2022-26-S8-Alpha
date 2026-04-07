import { useState } from 'react';
import { Database, ArrowRight, SkipForward, Server, CheckCircle, XCircle, Loader } from 'lucide-react';
import { DBConfig, defaultDBConfig, webgenService } from '../services/webgenService';

interface APIConfigProps {
  onConfigured: (config: DBConfig | null) => void;
}

export default function APIConfig({ onConfigured }: APIConfigProps) {
  const [dbConfig, setDbConfig] = useState<DBConfig>(defaultDBConfig);
  const [testing, setTesting] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'idle' | 'ok' | 'error'>('idle');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfigured(dbConfig);
  };

  const handleSkip = () => {
    onConfigured(null);
  };

  const handleTestConnection = async () => {
    setTesting(true);
    const ok = await webgenService.checkHealth();
    setBackendStatus(ok ? 'ok' : 'error');
    setTesting(false);
  };

  const updateConfig = (field: keyof DBConfig, value: string) => {
    setDbConfig(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="api-config-container">
      <div className="api-config-content">
        <div className="api-config-header">
          <Database size={48} />
          <h1>Database Settings</h1>
          <p>Configure your PostgreSQL database for dynamic websites, or skip for static sites</p>
        </div>

        {/* Backend status check */}
        <div style={{ marginBottom: '1.5rem' }}>
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={testing}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.5rem 1rem', borderRadius: '8px',
              background: backendStatus === 'ok' ? '#10b981' : backendStatus === 'error' ? '#ef4444' : '#374151',
              color: 'white', border: 'none', cursor: 'pointer', fontSize: '0.9rem',
              width: '100%', justifyContent: 'center',
            }}
          >
            {testing ? <Loader size={16} className="spinner" /> :
              backendStatus === 'ok' ? <CheckCircle size={16} /> :
                backendStatus === 'error' ? <XCircle size={16} /> :
                  <Server size={16} />}
            {testing ? 'Checking...' :
              backendStatus === 'ok' ? 'Backend Connected' :
                backendStatus === 'error' ? 'Backend Not Reachable — Start server first' :
                  'Test Backend Connection'}
          </button>
        </div>

        <form className="api-config-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="host">Host</label>
            <input
              type="text"
              id="host"
              value={dbConfig.host}
              onChange={(e) => updateConfig('host', e.target.value)}
              placeholder="localhost"
            />
          </div>

          <div className="form-group">
            <label htmlFor="port">Port</label>
            <input
              type="text"
              id="port"
              value={dbConfig.port}
              onChange={(e) => updateConfig('port', e.target.value)}
              placeholder="5433"
            />
          </div>

          <div className="form-group">
            <label htmlFor="user">User</label>
            <input
              type="text"
              id="user"
              value={dbConfig.user}
              onChange={(e) => updateConfig('user', e.target.value)}
              placeholder="postgres"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={dbConfig.password}
              onChange={(e) => updateConfig('password', e.target.value)}
              placeholder="Enter database password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="database">Database</label>
            <input
              type="text"
              id="database"
              value={dbConfig.database}
              onChange={(e) => updateConfig('database', e.target.value)}
              placeholder="postgres"
            />
          </div>

          <button type="submit" className="api-config-submit">
            Continue with Database
            <ArrowRight size={20} />
          </button>
        </form>

        <button
          onClick={handleSkip}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center',
            width: '100%', marginTop: '0.75rem', padding: '0.75rem',
            background: 'transparent', border: '1px solid rgba(255,255,255,0.15)',
            color: '#94a3b8', borderRadius: '8px', cursor: 'pointer', fontSize: '0.95rem',
          }}
        >
          <SkipForward size={18} />
          Skip — Generate static site (no database)
        </button>

        <div className="api-config-footer">
          <p>Database credentials are used only for generating backend code and are never stored on our servers.</p>
        </div>
      </div>
    </div>
  );
}
