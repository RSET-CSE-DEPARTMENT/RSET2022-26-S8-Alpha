import { useState } from 'react';
import LandingPage from './components/LandingPage';
import ModeSelection from './components/ModeSelection';
import APIConfig from './components/APIConfig';
import AIBuilderMode from './components/AIBuilderMode';
import Builder from './components/Builder';
import { DBConfig } from './services/webgenService';
import './App.css';

type AppView = 'landing' | 'mode-selection' | 'db-config' | 'ai-builder' | 'builder';

function App() {
  const [currentView, setCurrentView] = useState<AppView>('landing');
  const [dbConfig, setDbConfig] = useState<DBConfig | null>(null);

  const handleGetStarted = () => {
    setCurrentView('mode-selection');
  };

  const handleModeSelect = (mode: 'ai' | 'scratch') => {
    if (mode === 'ai') {
      setCurrentView('db-config');
    } else {
      setCurrentView('builder');
    }
  };

  const handleDBConfigured = (config: DBConfig | null) => {
    setDbConfig(config);
    setCurrentView('ai-builder');
  };

  const handleBack = () => {
    setCurrentView('landing');
  };

  return (
    <div className="app">
      {currentView === 'landing' && (
        <LandingPage onGetStarted={handleGetStarted} />
      )}
      {currentView === 'mode-selection' && (
        <ModeSelection onSelectMode={handleModeSelect} onBack={handleBack} />
      )}
      {currentView === 'db-config' && (
        <APIConfig onConfigured={handleDBConfigured} />
      )}
      {currentView === 'ai-builder' && (
        <AIBuilderMode dbConfig={dbConfig} />
      )}
      {currentView === 'builder' && (
        <Builder />
      )}
    </div>
  );
}

export default App;
