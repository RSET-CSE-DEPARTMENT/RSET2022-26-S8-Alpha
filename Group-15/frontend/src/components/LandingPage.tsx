import { Sparkles, Code, Palette, Zap } from 'lucide-react';

interface LandingPageProps {
  onGetStarted: () => void;
}

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  return (
    <div className="landing-page">
      <nav className="landing-nav">
        <div className="nav-content">
          <div className="logo">
            <Sparkles size={28} />
            <span>CHILLBUILD</span>
          </div>
          <button className="nav-cta" onClick={onGetStarted}>
            Get Started
          </button>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-content">
          <h1 className="hero-title">
            Build Websites with
            <span className="gradient-text"> AI & Drag-and-Drop</span>
          </h1>
          <p className="hero-description">
            Create stunning websites effortlessly. Use AI to generate designs or drag-and-drop
            components to build exactly what you envision. No coding required.
          </p>
          <button className="hero-cta" onClick={onGetStarted}>
            Start Building Free
            <Sparkles size={20} />
          </button>
        </div>
        <div className="hero-image">
          <div className="browser-mockup">
            <div className="browser-header">
              <div className="browser-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
            <div className="browser-content">
              <img
                src="https://images.pexels.com/photos/196644/pexels-photo-196644.jpeg?auto=compress&cs=tinysrgb&w=800"
                alt="Website builder preview"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="features">
        <h2 className="features-title">Everything You Need to Build</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <Sparkles size={24} />
            </div>
            <h3>AI-Powered Generation</h3>
            <p>
              Describe your vision and let AI create a complete website design in seconds.
              Choose from pre-built prompts or write your own.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
              <Code size={24} />
            </div>
            <h3>Visual Editor</h3>
            <p>
              Drag and drop components onto your canvas. See changes in real-time with live
              preview and code generation.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
              <Palette size={24} />
            </div>
            <h3>Full Style Control</h3>
            <p>
              Customize every aspect of your components. Change colors, sizes, spacing, and more
              with an intuitive properties panel.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' }}>
              <Zap size={24} />
            </div>
            <h3>Export & Deploy</h3>
            <p>
              Export clean HTML/CSS code or deploy your website instantly. Your designs are
              production-ready from day one.
            </p>
          </div>
        </div>
      </section>

      <section className="cta-section">
        <div className="cta-content">
          <h2>Ready to Start Building?</h2>
          <p>Join thousands of creators building beautiful websites with ChillBuild</p>
          <button className="cta-button" onClick={onGetStarted}>
            Launch Builder
            <Sparkles size={20} />
          </button>
        </div>
      </section>

      <footer className="landing-footer">
        <p>© 2024 ChillBuild. Built with creativity and code.</p>
      </footer>
    </div>
  );
}
