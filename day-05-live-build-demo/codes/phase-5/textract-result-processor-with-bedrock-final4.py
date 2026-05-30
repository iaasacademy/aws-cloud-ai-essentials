import json
import boto3

textract = boto3.client('textract')
bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')

OUTPUT_BUCKET = "AMAZON S3 BUCKET"

MODEL_ID = "BEDROCK APPLICATION INFERENCE ARN"

def lambda_handler(event, context):

    print("SNS EVENT RECEIVED:")
    print(json.dumps(event, indent=2))

    message = json.loads(event['Records'][0]['Sns']['Message'])

    job_id = message['JobId']
    status = message['Status']

    print(f"Job ID: {job_id}")
    print(f"Status: {status}")

    if status != "SUCCEEDED":
        print("Textract job failed")
        return

    # =========================
    # STEP 0 — GET S3 KEY + STYLE
    # =========================

    record = message['DocumentLocation']
    key = record['S3ObjectName']

    print(f"File key: {key}")

    if "modern" in key:
        style = "modern"
    elif "dark" in key:
        style = "dark"
    else:
        style = "minimal"

    print(f"Selected style: {style}")

    # =========================
    # STEP 1 — TEXTRACT TEXT
    # =========================

    extracted_text = []
    next_token = None

    while True:
        if next_token:
            response = textract.get_document_text_detection(
                JobId=job_id,
                NextToken=next_token
            )
        else:
            response = textract.get_document_text_detection(
                JobId=job_id
            )

        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                extracted_text.append(item['Text'])

        next_token = response.get('NextToken')

        if not next_token:
            break

    full_text = "\n".join(extracted_text)

    print("TEXT READY FOR BEDROCK")

    # =========================
    # STEP 2 — BEDROCK → JSON
    # =========================

    prompt = f"""
Extract structured resume data.

Return ONLY valid JSON:

{{
  "name": "",
  "summary": "",
  "linkedin_url": "",
  "key_achievements": [],
  "experience": [
    {{
      "title": "",
      "company": "",
      "start_date": "",
      "end_date": "",
      "responsibilities": []
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": ""
    }}
  ],
  "skills": []
}}

Rules:
- Use ALL information from the resume
- Extract Key Achievements as a separate array
- Extract the LinkedIn profile URL if present, otherwise leave linkedin_url as an empty string
- Do NOT merge achievements into the summary
- Do NOT omit anything
- Do NOT invent anything

Resume:
{full_text}
"""

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 3000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
    )

    result = json.loads(response['body'].read())

    json_text = result['content'][0]['text']
    json_text = json_text.replace("```json", "").replace("```", "").strip()

    content_json = json.loads(json_text)

    print("STRUCTURED DATA:")
    print(content_json)

    # =========================
    # STEP 3 — FORMAT DATA
    # =========================

    achievements_html = ''.join(
        f'<li class="achievement-item"><span class="achievement-icon">&#10003;</span>{achievement}</li>'
        for achievement in content_json.get('key_achievements', [])
    )

    experience_html = ""
    for exp in content_json.get('experience', []):
        experience_html += f"""
        <div class="exp-card">
            <div class="exp-header">
                <div>
                    <div class="exp-title">{exp.get('title','')}</div>
                    <div class="exp-company">{exp.get('company','')}</div>
                </div>
                <div class="exp-dates">{exp.get('start_date','')} &ndash; {exp.get('end_date','')}</div>
            </div>
            <ul class="resp-list">
                {''.join(f"<li>{resp}</li>" for resp in exp.get('responsibilities', []))}
            </ul>
        </div>
        """

    education_html = ''.join(
        f"""
        <div class="edu-item">
            <div class="edu-degree">{edu.get('degree','')}</div>
            <div class="edu-institution">{edu.get('institution','')}</div>
        </div>
        """
        for edu in content_json.get('education', [])
    )

    skills_html = ''.join(
        f"<span class='skill-tag'>{skill}</span>"
        for skill in content_json.get('skills', [])
    )

    # =========================
    # STEP 4 — STYLE CONFIG
    # =========================

    if style == "dark":
        bg_page        = "#0f1117"
        bg_sidebar     = "#1a1d27"
        bg_card        = "#1e2130"
        bg_card_border = "#2a2d3e"
        text_primary   = "#e8eaf0"
        text_secondary = "#9095a8"
        text_muted     = "#5c6070"
        accent_primary = "#6c63ff"
        accent_light   = "#2a2550"
        accent_text    = "#a89ffc"
        skill_bg       = "#252840"
        skill_text     = "#a89ffc"
        skill_border   = "#3a3860"
        exp_title_col  = "#ffffff"
        link_color     = "#6c63ff"
        nav_active_bg  = "#2a2550"
        nav_active_text= "#a89ffc"
        divider        = "#2a2d3e"
        header_gradient= "linear-gradient(135deg, #1a1d27 0%, #252840 100%)"
        avatar_bg      = "#2a2550"
        avatar_text    = "#a89ffc"
    elif style == "modern":
        bg_page        = "#f0f4ff"
        bg_sidebar     = "#ffffff"
        bg_card        = "#ffffff"
        bg_card_border = "#e2e8f5"
        text_primary   = "#1a202c"
        text_secondary = "#4a5568"
        text_muted     = "#a0aec0"
        accent_primary = "#4f46e5"
        accent_light   = "#eef2ff"
        accent_text    = "#4f46e5"
        skill_bg       = "#eef2ff"
        skill_text     = "#4338ca"
        skill_border   = "#c7d2fe"
        exp_title_col  = "#1a202c"
        link_color     = "#4f46e5"
        nav_active_bg  = "#eef2ff"
        nav_active_text= "#4338ca"
        divider        = "#e2e8f5"
        header_gradient= "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)"
        avatar_bg      = "#eef2ff"
        avatar_text    = "#4338ca"
    else:  # minimal
        bg_page        = "#f7f8fc"
        bg_sidebar     = "#ffffff"
        bg_card        = "#ffffff"
        bg_card_border = "#e4e8f0"
        text_primary   = "#1c1e29"
        text_secondary = "#52566b"
        text_muted     = "#9da3b8"
        accent_primary = "#2563eb"
        accent_light   = "#eff6ff"
        accent_text    = "#1d4ed8"
        skill_bg       = "#eff6ff"
        skill_text     = "#1e40af"
        skill_border   = "#bfdbfe"
        exp_title_col  = "#1c1e29"
        link_color     = "#2563eb"
        nav_active_bg  = "#eff6ff"
        nav_active_text= "#1e40af"
        divider        = "#e4e8f0"
        header_gradient= "linear-gradient(135deg, #1e40af 0%, #2563eb 100%)"
        avatar_bg      = "#dbeafe"
        avatar_text    = "#1e40af"

    name = content_json.get('name', 'Resume')
    initials = ''.join(part[0].upper() for part in name.split()[:2] if part)

    # =========================
    # STEP 5 — FINAL HTML
    # =========================

    linkedin_url = content_json.get('linkedin_url', '')
    linkedin_cta_html = f"""
        <div class="linkedin-cta">
            <a href="{linkedin_url}" target="_blank" rel="noopener" class="linkedin-btn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                View LinkedIn Profile
            </a>
        </div>""" if linkedin_url else ''

    html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: 'Inter', system-ui, sans-serif;
            background: {bg_page};
            color: {text_primary};
            min-height: 100vh;
            font-size: 15px;
            line-height: 1.6;
        }}

        /* ── LAYOUT ── */
        .layout {{
            display: flex;
            min-height: 100vh;
        }}

        /* ── SIDEBAR ── */
        .sidebar {{
            width: 260px;
            min-height: 100vh;
            background: {bg_sidebar};
            border-right: 1px solid {bg_card_border};
            position: fixed;
            top: 0;
            left: 0;
            display: flex;
            flex-direction: column;
        }}

        .sidebar-header {{
            background: {header_gradient};
            padding: 32px 24px 28px;
            text-align: center;
        }}

        .avatar {{
            width: 72px;
            height: 72px;
            border-radius: 50%;
            background: rgba(255,255,255,0.2);
            color: #fff;
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px;
            border: 3px solid rgba(255,255,255,0.35);
            letter-spacing: 1px;
        }}

        .sidebar-name {{
            color: #fff;
            font-size: 17px;
            font-weight: 600;
            letter-spacing: 0.2px;
        }}

        .sidebar-nav {{
            padding: 20px 16px;
            flex: 1;
        }}

        .nav-label {{
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: {text_muted};
            padding: 0 8px;
            margin-bottom: 6px;
        }}

        .nav-link {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 8px;
            text-decoration: none;
            color: {text_secondary};
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 2px;
            transition: background 0.15s, color 0.15s;
        }}

        .nav-link:hover {{
            background: {nav_active_bg};
            color: {nav_active_text};
        }}

        .nav-link .nav-icon {{
            width: 18px;
            height: 18px;
            opacity: 0.7;
            flex-shrink: 0;
        }}

        /* ── MAIN CONTENT ── */
        .main {{
            margin-left: 260px;
            flex: 1;
            padding: 36px 40px;
            max-width: 880px;
        }}

        /* ── SECTION HEADING ── */
        .section {{
            margin-bottom: 32px;
            scroll-margin-top: 32px;
        }}

        .section-heading {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
        }}

        .section-heading h2 {{
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: {accent_text};
        }}

        .section-heading::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: {divider};
        }}

        /* ── SUMMARY CARD ── */
        .summary-card {{
            background: {bg_card};
            border: 1px solid {bg_card_border};
            border-radius: 12px;
            padding: 24px 28px;
            color: {text_secondary};
            font-size: 15px;
            line-height: 1.75;
        }}

        /* ── ACHIEVEMENTS ── */
        .achievements-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 12px;
        }}

        .achievement-item {{
            list-style: none;
            background: {bg_card};
            border: 1px solid {bg_card_border};
            border-left: 3px solid {accent_primary};
            border-radius: 8px;
            padding: 14px 16px 14px 14px;
            font-size: 14px;
            color: {text_secondary};
            display: flex;
            align-items: flex-start;
            gap: 10px;
            line-height: 1.5;
        }}

        .achievement-icon {{
            color: {accent_primary};
            font-size: 13px;
            font-weight: 700;
            flex-shrink: 0;
            margin-top: 1px;
        }}

        /* ── EXPERIENCE ── */
        .exp-card {{
            background: {bg_card};
            border: 1px solid {bg_card_border};
            border-radius: 12px;
            padding: 22px 26px;
            margin-bottom: 14px;
        }}

        .exp-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 14px;
            gap: 12px;
        }}

        .exp-title {{
            font-size: 16px;
            font-weight: 600;
            color: {exp_title_col};
            margin-bottom: 4px;
        }}

        .exp-company {{
            font-size: 13px;
            font-weight: 500;
            color: {accent_text};
        }}

        .exp-dates {{
            font-size: 12px;
            font-weight: 500;
            color: {text_muted};
            background: {accent_light};
            padding: 4px 10px;
            border-radius: 20px;
            white-space: nowrap;
            flex-shrink: 0;
        }}

        .resp-list {{
            list-style: none;
            padding: 0;
            border-top: 1px solid {divider};
            padding-top: 14px;
        }}

        .resp-list li {{
            padding: 5px 0 5px 18px;
            font-size: 14px;
            color: {text_secondary};
            position: relative;
            line-height: 1.6;
        }}

        .resp-list li::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 13px;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: {accent_primary};
            opacity: 0.5;
        }}

        /* ── EDUCATION ── */
        .education-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .edu-item {{
            background: {bg_card};
            border: 1px solid {bg_card_border};
            border-radius: 10px;
            padding: 18px 22px;
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .edu-item::before {{
            content: '🎓';
            font-size: 22px;
            flex-shrink: 0;
        }}

        .edu-degree {{
            font-size: 15px;
            font-weight: 600;
            color: {exp_title_col};
            margin-bottom: 3px;
        }}

        .edu-institution {{
            font-size: 13px;
            color: {text_secondary};
        }}

        /* ── SKILLS ── */
        .skills-cloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .skill-tag {{
            background: {skill_bg};
            color: {skill_text};
            border: 1px solid {skill_border};
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 0.1px;
            transition: opacity 0.15s;
        }}

        .skill-tag:hover {{
            opacity: 0.8;
        }}


        /* ── LINKEDIN CTA ── */
        .linkedin-cta {{
            margin: 0 16px 24px;
        }}

        .linkedin-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            padding: 11px 16px;
            background: #0a66c2;
            color: #fff !important;
            text-decoration: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.1px;
            transition: background 0.15s, transform 0.1s;
        }}

        .linkedin-btn:hover {{
            background: #0958a8;
            transform: translateY(-1px);
        }}

        .linkedin-btn svg {{
            flex-shrink: 0;
        }}

        /* ── RESPONSIVE ── */
        @media (max-width: 768px) {{
            .sidebar {{
                display: none;
            }}
            .main {{
                margin-left: 0;
                padding: 24px 20px;
            }}
            .achievements-grid {{
                grid-template-columns: 1fr;
            }}
            .exp-header {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>

<div class="layout">

    <!-- SIDEBAR -->
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="avatar">{initials}</div>
            <div class="sidebar-name">{name}</div>
        </div>

        <nav class="sidebar-nav">
            <div class="nav-label">Navigation</div>
            <a href="#summary" class="nav-link">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
                Summary
            </a>
            <a href="#achievements" class="nav-link">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                Achievements
            </a>
            <a href="#experience" class="nav-link">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 3H8a2 2 0 0 0-2 2v2h12V5a2 2 0 0 0-2-2z"/></svg>
                Experience
            </a>
            <a href="#education" class="nav-link">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>
                Education
            </a>
            <a href="#skills" class="nav-link">
                <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                Skills
            </a>
        </nav>

        {linkedin_cta_html}
    </aside>

    <!-- MAIN -->
    <main class="main">

        <section class="section" id="summary">
            <div class="section-heading"><h2>Summary</h2></div>
            <div class="summary-card">{content_json.get('summary','')}</div>
        </section>

        <section class="section" id="achievements">
            <div class="section-heading"><h2>Key Achievements</h2></div>
            <ul class="achievements-grid">
                {achievements_html}
            </ul>
        </section>

        <section class="section" id="experience">
            <div class="section-heading"><h2>Experience</h2></div>
            {experience_html}
        </section>

        <section class="section" id="education">
            <div class="section-heading"><h2>Education</h2></div>
            <div class="education-list">
                {education_html}
            </div>
        </section>

        <section class="section" id="skills">
            <div class="section-heading"><h2>Skills</h2></div>
            <div class="skills-cloud">
                {skills_html}
            </div>
        </section>

    </main>
</div>

</body>
</html>
"""

    print("HTML GENERATED")

    # =========================
    # STEP 6 — SAVE TO S3
    # =========================

    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key="website/user1/index.html",
        Body=html_output,
        ContentType="text/html"
    )

    print("HTML UPLOADED TO S3")

    return {
        'statusCode': 200
    }