import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider } from '../context/AuthContext';
import { App } from '../App';

// Wrap helper
const renderApp = () => {
  return render(
    <AuthProvider>
      <App />
    </AuthProvider>
  );
};

describe('EVC Fleet Copilot Web Application (NOTE.md Phase 5)', () => {
  it('renders application navbar and default fleet overview successfully', async () => {
    renderApp();

    // Check navbar brand
    expect(screen.getByText(/EVC/i)).toBeInTheDocument();
    expect(screen.getAllByText(/COPILOT/i)[0]).toBeInTheDocument();

    // Check KPI cards
    await waitFor(() => {
      expect(screen.getByText(/Monitored Fleet/i)).toBeInTheDocument();
      expect(screen.getByText(/Fleet Health \(SoH\)/i)).toBeInTheDocument();
      expect(screen.getByText(/DP Cost Savings/i)).toBeInTheDocument();
    });
  });

  it('navigates to Live Alerts tab and displays open alerts', async () => {
    renderApp();

    const alertsTab = screen.getByRole('button', { name: /Live Alerts/i });
    fireEvent.click(alertsTab);

    // Verify Alerts view rendered
    expect(screen.getByText(/Real-Time Fleet Alerts/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/RANGE_RISK/i)).toBeInTheDocument();
    });
  });

  it('navigates to Vehicle & Plans tab and tests DP schedule optimizer', async () => {
    renderApp();

    const vehiclesTab = screen.getByRole('button', { name: /Vehicle & Plans/i });
    fireEvent.click(vehiclesTab);

    // Verify Vehicle detail loaded
    await waitFor(() => {
      expect(screen.getByText(/Battery-Aware DP Charge Optimiser/i)).toBeInTheDocument();
      expect(screen.getByText(/24-Hour Telemetry Time-Series/i)).toBeInTheDocument();
    });

    // Propose plan button click
    const proposeBtn = screen.getByRole('button', { name: /Compute Optimal Charging Schedule/i });
    expect(proposeBtn).toBeInTheDocument();
    fireEvent.click(proposeBtn);

    await waitFor(() => {
      expect(screen.getByText(/Optimal charging plan computed via Dynamic Programming/i)).toBeInTheDocument();
      expect(screen.getByText(/Net Savings/i)).toBeInTheDocument();
    });
  });

  it('navigates to Copilot Chat and tests prompt interaction', async () => {
    renderApp();

    const copilotTab = screen.getByRole('button', { name: /Copilot Chat/i });
    fireEvent.click(copilotTab);

    expect(screen.getByText(/AI Copilot Intelligence/i)).toBeInTheDocument();
    expect(screen.getByText(/LangGraph Tool Execution Trace/i)).toBeInTheDocument();

    // Send a message
    const input = screen.getByPlaceholderText(/Ask Copilot about vehicle battery/i);
    const sendBtn = screen.getByRole('button', { name: /Send/i });

    fireEvent.change(input, { target: { value: 'Explain thermal alert' } });
    fireEvent.click(sendBtn);

    await waitFor(
      () => {
        expect(screen.getByText(/NordMotors Polar-4/i)).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('navigates to Compliance & Admin and demonstrates DP benchmark', async () => {
    renderApp();

    const adminTab = screen.getByRole('button', { name: /Compliance & Admin/i });
    fireEvent.click(adminTab);

    expect(screen.getByText(/Compliance, Privacy & Security Admin/i)).toBeInTheDocument();
    expect(screen.getByText(/Role-Based Location Masking Proof/i)).toBeInTheDocument();
    expect(screen.getByText(/Differential Privacy SoH Benchmark/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Immutable Compliance Audit Trail/i)).toBeInTheDocument();
    });
  });

  it('proves role-aware location masking when switching to Viewer role', async () => {
    renderApp();

    // Click Viewer role in header
    const viewerBtn = screen.getByRole('button', { name: /Viewer \(Masked\)/i });
    fireEvent.click(viewerBtn);

    // Verify masking indicator turns active
    await waitFor(() => {
      expect(screen.getByText(/Role-Aware Privacy Active: Masked to geohash5/i)).toBeInTheDocument();
    });
  });
});
