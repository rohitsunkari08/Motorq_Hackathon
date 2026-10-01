import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Zap, Shield, KeyRound, AlertCircle, ArrowRight, CheckCircle2 } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState('manager@voltfleet.com');
  const [password, setPassword] = useState('Password123!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoAccount = (role: 'manager' | 'viewer' | 'admin') => {
    if (role === 'manager') setEmail('manager@voltfleet.com');
    else if (role === 'viewer') setEmail('viewer@voltfleet.com');
    else if (role === 'admin') setEmail('admin@voltfleet.com');
    setPassword('Password123!');
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        position: 'relative',
        zIndex: 2,
      }}
    >
      <div
        className="card"
        style={{
          maxWidth: '480px',
          width: '100%',
          padding: '40px 36px',
          border: '1px solid rgba(0, 240, 255, 0.2)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7), var(--shadow-glow-cyan)',
        }}
      >
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: 'var(--radius-lg)',
              background: 'linear-gradient(135deg, #00f0ff 0%, #8b5cf6 100%)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
              boxShadow: 'var(--shadow-glow-cyan)',
            }}
          >
            <Zap size={28} color="#05101a" strokeWidth={2.5} />
          </div>
          <h1 style={{ fontSize: '1.75rem', marginBottom: '8px' }}>EVC Fleet Intelligence</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Battery-Health & Smart Charging Copilot
          </p>
        </div>

        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              background: 'var(--accent-rose-dim)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: 'var(--accent-rose)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              marginBottom: '20px',
              fontSize: '0.85rem',
            }}
          >
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="input-email">
              Enterprise Email
            </label>
            <input
              id="input-email"
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="manager@voltfleet.com"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="input-password">
              Password
            </label>
            <input
              id="input-password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
          </div>

          <button
            id="btn-login-submit"
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '12px', marginTop: '10px', fontSize: '0.95rem' }}
            disabled={loading}
          >
            {loading ? 'Authenticating with RS256 JWT...' : 'Sign In to Fleet Portal'}
            {!loading && <ArrowRight size={18} />}
          </button>
        </form>

        {/* 1-Click Demo Accounts */}
        <div style={{ marginTop: '28px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Quick Demo Credentials (Argon2id + JWT):
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
            <button
              id="btn-demo-manager"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setDemoAccount('manager')}
              style={{ fontSize: '0.75rem', padding: '8px 4px' }}
            >
              Fleet Manager
            </button>
            <button
              id="btn-demo-viewer"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setDemoAccount('viewer')}
              style={{ fontSize: '0.75rem', padding: '8px 4px' }}
            >
              Viewer (Masked)
            </button>
            <button
              id="btn-demo-admin"
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setDemoAccount('admin')}
              style={{ fontSize: '0.75rem', padding: '8px 4px' }}
            >
              Admin / Erasure
            </button>
          </div>
        </div>

        {/* Security assurance */}
        <div style={{ marginTop: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <Shield size={14} color="var(--accent-emerald)" />
          <span>OAuth2 / RS256 Tokens · Tenant Isolation · OWASP Top 10</span>
        </div>
      </div>
    </div>
  );
};
