import React, { useState } from 'react';

interface Props {
  dark: boolean;
}

type Screen = 'login' | 'dashboard' | 'jobs' | 'jobDetail' | 'profile';

const SCREENS: { key: Screen; label: string }[] = [
  { key: 'login', label: 'Login' },
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'jobs', label: 'Jobs' },
  { key: 'jobDetail', label: 'Job Detail' },
  { key: 'profile', label: 'Profile' },
];

const MOCK_JOBS = [
  {
    id: '1',
    internalRef: 'IT-2026-001847',
    serviceType: 'ARR',
    status: 'PENDING',
    route: 'Cairo Airport (T2) \u2192 Pyramids Zone',
    pax: 4,
    time: '14:30',
    driver: 'Mohamed Khalil',
    vehicle: 'Toyota Hiace - ABC 1234',
  },
  {
    id: '2',
    internalRef: 'IT-2026-001852',
    serviceType: 'DEP',
    status: 'IN_PROGRESS',
    route: 'Le Meridien Hotel \u2192 Cairo Airport (T3)',
    pax: 2,
    time: '16:00',
    driver: 'Hassan Ali',
    vehicle: 'Toyota Corolla - DEF 5678',
  },
  {
    id: '3',
    internalRef: 'IT-2026-001860',
    serviceType: 'CITY',
    status: 'COMPLETED',
    route: 'Four Seasons Nile \u2192 Khan el-Khalili',
    pax: 6,
    time: '09:00',
    driver: 'Youssef Magdy',
    vehicle: 'Mercedes Sprinter - GHI 9012',
  },
  {
    id: '4',
    internalRef: 'IT-2026-001865',
    serviceType: 'ARR',
    status: 'PENDING',
    route: 'Cairo Airport (T1) \u2192 Maadi Zone',
    pax: 3,
    time: '18:00',
    driver: 'Ahmed Samir',
    vehicle: 'Toyota Hiace - JKL 3456',
  },
];

const MOCK_VEHICLES = [
  { name: 'Toyota Hiace', plate: 'ABC 1234', capacity: 10, status: 'Active' },
  { name: 'Toyota Corolla', plate: 'DEF 5678', capacity: 4, status: 'Active' },
  { name: 'Mercedes Sprinter', plate: 'GHI 9012', capacity: 14, status: 'Active' },
  { name: 'Toyota Hiace', plate: 'JKL 3456', capacity: 10, status: 'Active' },
  { name: 'Hyundai H1', plate: 'MNO 7890', capacity: 8, status: 'Maintenance' },
];

const MOCK_DRIVERS = [
  { name: 'Mohamed Khalil', mobile: '+20 100 234 5678', status: 'On Trip' },
  { name: 'Hassan Ali', mobile: '+20 101 345 6789', status: 'On Trip' },
  { name: 'Youssef Magdy', mobile: '+20 102 456 7890', status: 'Available' },
  { name: 'Ahmed Samir', mobile: '+20 103 567 8901', status: 'Available' },
  { name: 'Omar Fathy', mobile: '+20 104 678 9012', status: 'Off Duty' },
];

function getBorderColor(status: string) {
  switch (status) {
    case 'PENDING': return '#eab308';
    case 'IN_PROGRESS': return '#3b82f6';
    case 'COMPLETED': return '#22c55e';
    default: return '#eab308';
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'PENDING': return <span className="badge badge-pending">Pending</span>;
    case 'IN_PROGRESS': return <span className="badge badge-progress">In Progress</span>;
    case 'COMPLETED': return <span className="badge badge-completed">Completed</span>;
    default: return null;
  }
}

function getServiceBadge(type: string) {
  switch (type) {
    case 'ARR': return <span className="badge badge-arr">ARR</span>;
    case 'DEP': return <span className="badge badge-dep">DEP</span>;
    case 'CITY': return <span className="badge badge-city">CITY</span>;
    default: return null;
  }
}

function getDriverStatusColor(status: string) {
  switch (status) {
    case 'On Trip': return '#3b82f6';
    case 'Available': return '#22c55e';
    case 'Off Duty': return '#737373';
    default: return '#737373';
  }
}

export function SupplierApp({ dark }: Props) {
  const [screen, setScreen] = useState<Screen>('dashboard');
  const [activeTab, setActiveTab] = useState(0);

  const tabForScreen = (s: Screen) => {
    if (s === 'dashboard') return 0;
    if (s === 'jobs' || s === 'jobDetail') return 1;
    if (s === 'profile') return 2;
    return -1;
  };

  const renderLogin = () => (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-title">iTour Supplier</div>
        <input className="login-input" placeholder="Company Email" />
        <input className="login-input" type="password" placeholder="Password" />
        <button className="login-btn">Sign In</button>
        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
          Forgot password? Contact iTour support
        </div>
      </div>
    </div>
  );

  const renderDashboard = () => (
    <>
      <div className="screen-header">Dashboard</div>
      <div style={{ padding: '12px 16px 0' }}>
        <div style={{ fontSize: 13, color: '#737373' }}>Thursday, February 20, 2026</div>
        <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>Welcome, Nile Transport Co.</div>
      </div>

      <div style={{ padding: '8px 16px' }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Today's Overview</div>
      </div>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#3b82f6' }}>12</div>
          <div className="stat-label">Total Jobs</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#22c55e' }}>8</div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#eab308' }}>4</div>
          <div className="stat-label">Pending</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#8b5cf6' }}>0</div>
          <div className="stat-label">No Shows</div>
        </div>
      </div>

      <div style={{ padding: '16px 16px 0' }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Fleet Status</div>
      </div>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">15</div>
          <div className="stat-label">Vehicles</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">12</div>
          <div className="stat-label">Drivers</div>
        </div>
      </div>

      <div style={{ padding: '16px 16px 8px' }}>
        <div style={{ fontSize: 14, fontWeight: 600 }}>Driver Availability</div>
      </div>
      {MOCK_DRIVERS.slice(0, 3).map((d, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 16px', borderBottom: '1px solid ' + (dark ? '#1a1a1a' : '#f0f0f0') }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500 }}>{d.name}</div>
            <div style={{ fontSize: 12, color: '#737373' }}>{d.mobile}</div>
          </div>
          <span className="badge" style={{ background: getDriverStatusColor(d.status) + '20', color: getDriverStatusColor(d.status) }}>
            {d.status}
          </span>
        </div>
      ))}
      <div style={{ height: 80 }} />
    </>
  );

  const renderJobs = () => (
    <>
      <div className="screen-header">Jobs</div>
      <div className="date-nav">
        <button>&larr;</button>
        <span>Thu, Feb 20, 2026</span>
        <button>&rarr;</button>
      </div>
      {MOCK_JOBS.map((job) => (
        <div
          key={job.id}
          className="job-card"
          style={{ borderLeftColor: getBorderColor(job.status), cursor: 'pointer' }}
          onClick={() => setScreen('jobDetail')}
        >
          <div className="job-card-header">
            <div style={{ display: 'flex', gap: 6 }}>
              {getServiceBadge(job.serviceType)}
              {getStatusBadge(job.status)}
            </div>
            <span style={{ fontSize: 13, color: '#737373' }}>{job.time}</span>
          </div>
          <div className="job-ref">{job.internalRef}</div>
          <div className="job-route">{job.route}</div>
          <div className="job-footer">
            <span>{job.pax} pax</span>
            <span>{job.driver}</span>
          </div>
          <div style={{ fontSize: 12, color: '#737373', marginTop: 4 }}>{job.vehicle}</div>
          {job.status === 'PENDING' && (
            <div className="btn-row">
              <button className="btn btn-primary btn-sm" style={{ flex: 1 }}>Mark Complete</button>
            </div>
          )}
          {job.status === 'IN_PROGRESS' && (
            <div className="btn-row">
              <button className="btn btn-primary btn-sm" style={{ flex: 1 }}>Mark Complete</button>
            </div>
          )}
        </div>
      ))}
      <div style={{ height: 80 }} />
    </>
  );

  const renderJobDetail = () => {
    const job = MOCK_JOBS[0];
    return (
      <>
        <div className="screen-header" style={{ position: 'relative' }}>
          <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('jobs')}>&larr;</span>
          Job Detail
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {getServiceBadge(job.serviceType)}
            {getStatusBadge(job.status)}
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{job.internalRef}</div>
          <div style={{ fontSize: 14, color: '#737373', marginBottom: 16 }}>{job.route}</div>

          <div className="card" style={{ margin: '0 0 12px' }}>
            <div className="card-title">Trip Info</div>
            <div className="info-row"><span className="info-label">Service</span><span className="info-value">{job.serviceType}</span></div>
            <div className="info-row"><span className="info-label">Time</span><span className="info-value">{job.time}</span></div>
            <div className="info-row"><span className="info-label">Pax</span><span className="info-value">{job.pax} passengers</span></div>
          </div>

          <div className="card" style={{ margin: '0 0 12px' }}>
            <div className="card-title">Assignment</div>
            <div className="info-row"><span className="info-label">Driver</span><span className="info-value">{job.driver}</span></div>
            <div className="info-row"><span className="info-label">Vehicle</span><span className="info-value">{job.vehicle}</span></div>
          </div>

          <div className="form-group">
            <label className="form-label">Completion Notes</label>
            <input className="form-input" placeholder="Add any notes about this trip..." />
          </div>

          <button className="btn btn-primary">Mark Complete</button>
        </div>
        <div style={{ height: 80 }} />
      </>
    );
  };

  const renderProfile = () => (
    <>
      <div className="screen-header">Company Profile</div>
      <div style={{ padding: 16 }}>
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <div style={{ width: 72, height: 72, borderRadius: '50%', background: dark ? '#262626' : '#e5e5e5', margin: '0 auto 12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 700 }}>
            NT
          </div>
          <div className="profile-name">Nile Transport Co.</div>
          <span className="badge badge-completed">Verified Supplier</span>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Company Info</div>
          <div className="profile-field">
            <div className="profile-field-label">Legal Name</div>
            <div className="profile-field-value">Nile Transport & Tourism LLC</div>
          </div>
          <div className="profile-field">
            <div className="profile-field-label">Phone</div>
            <div className="profile-field-value">+20 2 2345 6789</div>
          </div>
          <div className="profile-field">
            <div className="profile-field-label">Email</div>
            <div className="profile-field-value">ops@niletransport.com.eg</div>
          </div>
          <div className="profile-field">
            <div className="profile-field-label">Tax Registration</div>
            <div className="profile-field-value">TAX-2024-98765</div>
          </div>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Vehicles ({MOCK_VEHICLES.length})</div>
          {MOCK_VEHICLES.map((v, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: i < MOCK_VEHICLES.length - 1 ? '1px solid ' + (dark ? '#262626' : '#f0f0f0') : 'none' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{v.name}</div>
                <div style={{ fontSize: 12, color: '#737373' }}>{v.plate} - {v.capacity} pax</div>
              </div>
              <span className="badge" style={{
                background: v.status === 'Active' ? '#d1fae5' : '#fef3c7',
                color: v.status === 'Active' ? '#065f46' : '#92400e'
              }}>
                {v.status}
              </span>
            </div>
          ))}
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Drivers ({MOCK_DRIVERS.length})</div>
          {MOCK_DRIVERS.map((d, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: i < MOCK_DRIVERS.length - 1 ? '1px solid ' + (dark ? '#262626' : '#f0f0f0') : 'none' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{d.name}</div>
                <div style={{ fontSize: 12, color: '#737373' }}>{d.mobile}</div>
              </div>
              <span className="badge" style={{ background: getDriverStatusColor(d.status) + '20', color: getDriverStatusColor(d.status) }}>
                {d.status}
              </span>
            </div>
          ))}
        </div>

        <button className="btn btn-destructive" style={{ marginTop: 8 }}>Sign Out</button>
      </div>
      <div style={{ height: 80 }} />
    </>
  );

  const renderScreen = () => {
    switch (screen) {
      case 'login': return renderLogin();
      case 'dashboard': return renderDashboard();
      case 'jobs': return renderJobs();
      case 'jobDetail': return renderJobDetail();
      case 'profile': return renderProfile();
    }
  };

  return (
    <div>
      <div className="screen-nav">
        {SCREENS.map((s) => (
          <button
            key={s.key}
            className={`screen-pill ${screen === s.key ? 'active' : ''}`}
            onClick={() => { setScreen(s.key); setActiveTab(tabForScreen(s.key)); }}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className={`phone-frame ${dark ? 'dark' : ''}`}>
        <div className="phone-notch" />
        <div className="phone-screen">
          {renderScreen()}
        </div>
        {screen !== 'login' && (
          <div className="tab-bar">
            <div className={`tab-item ${activeTab === 0 ? 'active' : ''}`} onClick={() => { setActiveTab(0); setScreen('dashboard'); }}>
              <div className="tab-icon">&#128200;</div>
              <span>Dashboard</span>
            </div>
            <div className={`tab-item ${activeTab === 1 ? 'active' : ''}`} onClick={() => { setActiveTab(1); setScreen('jobs'); }}>
              <div className="tab-icon">&#128203;</div>
              <span>Jobs</span>
            </div>
            <div className={`tab-item ${activeTab === 2 ? 'active' : ''}`} onClick={() => { setActiveTab(2); setScreen('profile'); }}>
              <div className="tab-icon">&#127970;</div>
              <span>Profile</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
