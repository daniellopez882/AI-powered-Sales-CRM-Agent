import React, { useState, useEffect } from 'react';

const Dashboard = () => {
    const [stats, setStats] = useState({
        pipelineValue: "$1.2M",
        dealsWon: 12,
        activeLeads: 45
    });

    return (
        <div style={{ padding: '20px', fontFamily: 'Arial', backgroundColor: '#f4f7f6', minHeight: '100vh' }}>
            <h1 style={{ color: '#2c3e50' }}>SalesIQ CRM Dashboard</h1>

            <div style={{ display: 'flex', gap: '20px', marginBottom: '30px' }}>
                <div style={cardStyle}>
                    <h3>Pipeline Value</h3>
                    <p style={valueStyle}>{stats.pipelineValue}</p>
                </div>
                <div style={cardStyle}>
                    <h3>Deals Won</h3>
                    <p style={valueStyle}>{stats.dealsWon}</p>
                </div>
                <div style={cardStyle}>
                    <h3>Active Leads</h3>
                    <p style={valueStyle}>{stats.activeLeads}</p>
                </div>
            </div>

            <div style={cardStyle}>
                <h3>Recent AI Insights</h3>
                <ul>
                    <li><strong>LeadEnricher:</strong> 5 new hot leads identified in the SaaS sector.</li>
                    <li><strong>EmailPersonalizer:</strong> Reply rate increased by 15% with "Curiosity" subject lines.</li>
                    <li><strong>DealAnalyzer:</strong> 3 deals at risk due to inactivity > 14 days.</li>
                </ul>
            </div>
        </div>
    );
};

const cardStyle = {
    backgroundColor: '#fff',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    flex: 1
};

const valueStyle = {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#3498db'
};

export default Dashboard;
