def generate_shift_html_report(stats, date_str, shift_label):
    # Calculate Percentages
    total = stats['total_processed']
    sent_rate = (stats['total_sent'] / total * 100) if total > 0 else 0
    draft_rate = (stats['total_drafts'] / total * 100) if total > 0 else 0
    
    # AI Performance Insight
    if sent_rate >= 90:
        performance_msg = "🌟 Excellent! AI is handling most queries autonomously."
        perf_color = "#27ae60"
    elif sent_rate >= 70:
        performance_msg = "✅ Good. Some human intervention is required."
        perf_color = "#f39c12"
    else:
        performance_msg = "⚠️ Needs Attention. High rate of human drafts."
        perf_color = "#c0392b"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; border-left: 5px solid #e67e22; padding-left: 10px; }}
            .summary-card {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .card {{ flex: 1; background: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; }}
            .card.highlight {{ background: #dff9fb; border: 1px solid #c7ecee; }}
            .card h4 {{ margin: 0 0 10px; color: #7f8c8d; font-size: 0.9em; text-transform: uppercase; }}
            .card .number {{ font-size: 2.5em; font-weight: bold; color: #2980b9; }}
            
            /* Table Styling Enhancements */
            table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 15px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #eee; font-size: 0.95em; }}
            th {{ background-color: #f8f9fa; color: #444; font-weight: 600; text-transform: uppercase; font-size: 0.85em; letter-spacing: 0.5px; }}
            tr:last-child td {{ border-bottom: none; }}
            tr:hover {{ background-color: #fcfcfc; }}
            
            /* Status Badges */
            .tag {{ padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 500; }}
            .tag-inquiry {{ background: #e3f2fd; color: #1565c0; }}
            .tag-summary {{ color: #444; font-size: 0.9em; line-height: 1.6; display: block; }}
            
            /* Interaction Types */
            .type-badge {{ font-size: 0.75em; font-weight: bold; padding: 3px 6px; border-radius: 3px; text-transform: uppercase; }}
            .type-pending {{ background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }} /* Yellow */
            .type-approved {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }} /* Green */
            .type-edited {{ background: #d6d8d9; color: #1b1e21; border: 1px solid #c6c8ca; }} /* Grey/Silver */
            .type-human {{ background: #cce5ff; color: #004085; border: 1px solid #b8daff; }} /* Blue */
            
            /* Chart & Progress Styles */
            .chart-container {{ display: flex; align-items: center; gap: 40px; background: #fafafa; padding: 20px; border-radius: 8px; margin-top: 20px; }}
            .pie-chart {{
                width: 120px; height: 120px; border-radius: 50%;
                background: conic-gradient(#27ae60 0% {sent_rate}%, #f39c12 {sent_rate}% 100%);
                position: relative;
            }}
            .pie-chart::after {{
                content: "{int(sent_rate)}%"; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                background: white; width: 80px; height: 80px; border-radius: 50%;
                display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.2em; color: #2c3e50;
            }}
            .chart-legend {{ flex: 1; }}
            .legend-item {{ margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; }}
            .bar-bg {{ flex: 1; height: 10px; background: #e0e0e0; border-radius: 5px; margin: 0 15px; overflow: hidden; }}
            .bar-fill {{ height: 100%; border-radius: 5px; }}
            .insight-box {{ margin-top: 15px; padding: 10px; border-left: 4px solid {perf_color}; background: #fff; color: {perf_color}; font-weight: bold; }}
            .sharm-section {{ background-color: #fff3e0; padding: 20px; border-radius: 8px; margin-top: 30px; border: 1px solid #ffe0b2; }}
            .footer {{ margin-top: 40px; text-align: center; font-size: 0.8em; color: #aaa; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Shift Report: {shift_label}</h1>
            <p><strong>Date:</strong> {date_str} (Cairo Time)</p>
            
            <div class="summary-card">
                <div class="card highlight">
                    <h4>Total Processed</h4>
                    <div class="number">{stats['total_processed']}</div>
                </div>
                <div class="card">
                    <h4>Auto-Replied</h4>
                    <div class="number" style="color: #27ae60;">{stats['total_sent']}</div>
                </div>
                <div class="card">
                    <h4>Drafts (Review)</h4>
                    <div class="number" style="color: #f39c12;">{stats['total_drafts']}</div>
                </div>
            </div>

            <h2>🧠 AI Quality & Performance</h2>
            <div class="chart-container">
                <div class="pie-chart"></div>
                <div class="chart-legend">
                    <div class="legend-item">
                        <span style="color:#27ae60;">● Auto-Replied</span>
                        <div class="bar-bg"><div class="bar-fill" style="width: {sent_rate}%; background: #27ae60;"></div></div>
                        <span>{int(sent_rate)}%</span>
                    </div>
                    <div class="legend-item">
                        <span style="color:#f39c12;">● Human Drafts</span>
                        <div class="bar-bg"><div class="bar-fill" style="width: {draft_rate}%; background: #f39c12;"></div></div>
                        <span>{int(draft_rate)}%</span>
                    </div>
                    <div class="insight-box">
                        {performance_msg}
                    </div>
                </div>
            </div>

            <h2>🐫 Sharm El Sheikh (Special Region)</h2>
            <div class="sharm-section">
                <table>
                    <tr><th>Metric</th><th>Count</th></tr>
                    <tr><td>Total Interactions</td><td>{stats['sharm']['total']}</td></tr>
                    <tr><td>Auto-Replied</td><td>{stats['sharm']['sent']}</td></tr>
                    <tr><td>Drafts Created</td><td>{stats['sharm']['drafts']}</td></tr>
                    <tr><td>Top Inquiries</td><td>{', '.join([f"{k} ({v})" for k,v in stats['sharm']['inquiries'].most_common(3)]) or 'None'}</td></tr>
                </table>
            </div>

            <h2>🔥 Top Inquiries (This Shift)</h2>
            <table>
                <thead>
                    <tr><th>Inquiry Type</th><th>Count</th></tr>
                </thead>
                <tbody>
    """
    
    for inquiry, count in stats['global_inquiries'].most_common(5):
        html += f"<tr><td>{inquiry}</td><td>{count}</td></tr>"
        
    html += """
                </tbody>
            </table>
            
            <h2>🗣️ Top Recurring Issues (AI Analysis)</h2>
            <p>Grouped by semantic similarity using AI to identify core recurring topics.</p>
            <table>
                <thead>
                    <tr><th>Issue / Topic</th><th>Count</th></tr>
                </thead>
                <tbody>
    """
    
    # Use AI grouped questions if available, else fallback to counter
    top_qs = stats.get('top_questions_grouped')
    
    if top_qs:
        for topic, count in top_qs:
            html += f"<tr><td><strong>{topic}</strong></td><td><span class='tag' style='background:#eee;'>{count}</span></td></tr>"
    elif stats.get('top_questions'):
        # Fallback to old method if AI failed
        for question, count in stats['top_questions'].most_common(5):
             html += f"<tr><td>{question}</td><td>{count}</td></tr>"
    else:
        html += "<tr><td colspan='2' style='text-align:center; color:#999;'>No significant recurring questions found.</td></tr>"

    html += """
                </tbody>
            </table>
            
            <h2>📝 Interaction Log (Drafts & Reviews)</h2>
            <p>Detailed breakdown of AI drafts, human edits, and direct interventions.</p>
            <table>
                <thead>
                    <tr>
                        <th style="width:15%">Booking / Email</th>
                        <th style="width:15%">Type</th>
                        <th style="width:15%">Inquiry</th>
                        <th style="width:55%">AI Summary / Context</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    if stats['draft_details']:
        for draft in stats['draft_details']:
            summary = draft.get('summary', 'N/A')
            inquiry = draft['inquiry']
            itype = draft.get('type', 'UNKNOWN')
            
            # Map type to CSS class and Label
            if itype == 'DRAFT_PENDING':
                badge_class = 'type-pending'
                badge_label = '⏳ Pending Review'
            elif itype == 'DRAFT_APPROVED':
                badge_class = 'type-approved'
                badge_label = '✅ AI Approved'
            elif itype == 'DRAFT_EDITED':
                badge_class = 'type-edited'
                badge_label = '✏️ Human Edited'
            elif itype == 'HUMAN_REPLY':
                badge_class = 'type-human'
                badge_label = '👤 Human Reply'
            else:
                badge_class = 'type-edited'
                badge_label = itype
                
            html += f"""
            <tr>
                <td><strong>{draft['booking_nr']}</strong><br><span style="font-size:0.8em; color:#888;">{draft['email']}</span></td>
                <td><span class="type-badge {badge_class}">{badge_label}</span></td>
                <td><span class="tag tag-inquiry">{inquiry}</span></td>
                <td class="tag-summary">{summary}</td>
            </tr>
            """
    else:
        html += "<tr><td colspan='4' style='text-align:center;'>No significant interactions recorded in this shift.</td></tr>"

    html += """
                </tbody>
            </table>

            <div class="footer">
                Generated by FTS AI Agent System • Shift Auto-Report
            </div>
        </div>
    </body>
    </html>
    """
    return html
