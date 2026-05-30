import React, { useState, useCallback, useRef, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "react-toastify";
import {
  RadialBarChart, RadialBar, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  CartesianGrid, Legend, PieChart, Pie, ComposedChart, Area, Line,
} from "recharts";
import axios from "axios";
import { useTheme } from "./App";

const API = "http://localhost:8000";
const getToken = () => localStorage.getItem("access_token");
const authHdr  = () => ({ Authorization: `Bearer ${getToken()}` });

const EMOTION_EMOJI  = { happy:"😊", sad:"😢", angry:"😠", neutral:"😐", surprise:"😲", fear:"😨", disgust:"🤢", unknown:"❓" };
const EMOTION_COLOR  = { happy:"#10b981", sad:"#6366f1", angry:"#ef4444", neutral:"#94a3b8", surprise:"#f59e0b", fear:"#8b5cf6", disgust:"#06b6d4", unknown:"#64748b" };
const EMOTION_BG     = { happy:"rgba(16,185,129,0.12)", sad:"rgba(99,102,241,0.12)", angry:"rgba(239,68,68,0.12)", neutral:"rgba(148,163,184,0.12)", surprise:"rgba(245,158,11,0.12)", fear:"rgba(139,92,246,0.12)", disgust:"rgba(6,182,212,0.12)", unknown:"rgba(100,116,139,0.12)" };

const NAV = [
  { id:"analyze",   icon:"🔍", label:"Analyze"   },
  { id:"batch",     icon:"📦", label:"Batch"      },
  { id:"compare",   icon:"⚖️",  label:"Compare"   },
  { id:"webcam",    icon:"📷", label:"Live Cam"   },
  { id:"history",   icon:"📋", label:"History"    },
  { id:"analytics", icon:"📊", label:"Analytics"  },
  { id:"insights",  icon:"💡", label:"Insights"   },
  { id:"profile",   icon:"👤", label:"Profile"    },
];

// ── Helpers ───────────────────────────────────────────────────────
function PageHeader({ title, subtitle, noMargin }) {
  return (
    <div style={{ marginBottom: noMargin ? 0 : "28px" }}>
      <h1 style={{ fontSize: "26px", fontWeight: "900", lineHeight: 1.2 }}>{title}</h1>
      {subtitle && <p style={{ color: "var(--text3)", marginTop: "6px", fontSize: "14px" }}>{subtitle}</p>}
    </div>
  );
}
function LoadingState({ text = "Loading..." }) {
  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", padding:"80px 0", gap:"16px" }}>
      <div style={{ width:"44px", height:"44px", border:"3px solid var(--border)", borderTopColor:"var(--primary)", borderRadius:"50%" }} className="spin" />
      <p style={{ color:"var(--text3)", fontSize:"14px" }}>{text}</p>
    </div>
  );
}
function Row({ label, value, color }) {
  return (
    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"4px 0" }}>
      <span style={{ color:"var(--text3)", fontSize:"12px" }}>{label}</span>
      <span style={{ fontWeight:"600", fontSize:"13px", color: color || "var(--text)" }}>{value}</span>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────
function Sidebar({ tab, setTab, sidebarOpen, setSidebarOpen, onLogout }) {
  const { theme, toggleTheme } = useTheme();
  return (
    <aside style={{ width: sidebarOpen ? "230px" : "68px", background: "var(--bg2)", borderRight: "1px solid var(--border)", display:"flex", flexDirection:"column", transition:"width 0.3s cubic-bezier(0.4,0,0.2,1)", flexShrink:0, position:"sticky", top:0, height:"100vh", zIndex:20, overflow:"hidden" }}>
      {/* Logo */}
      <div style={{ padding:"18px 14px", borderBottom:"1px solid var(--border)", display:"flex", alignItems:"center", gap:"12px", minHeight:"68px" }}>
        <div style={{ width:"38px", height:"38px", background:"linear-gradient(135deg,#6366f1,#06b6d4)", borderRadius:"12px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"18px", flexShrink:0, boxShadow:"0 0 20px rgba(99,102,241,0.5)" }}>🤖</div>
        {sidebarOpen && <div><div style={{ fontWeight:"800", fontSize:"14px", whiteSpace:"nowrap" }} className="gradient-text">AI Analysis</div><div style={{ fontSize:"10px", color:"var(--text3)", whiteSpace:"nowrap" }}>Face Intelligence</div></div>}
      </div>

      {/* Nav */}
      <nav style={{ flex:1, padding:"10px 8px", display:"flex", flexDirection:"column", gap:"2px", overflowY:"auto" }}>
        {NAV.map((n) => (
          <button key={n.id} onClick={() => setTab(n.id)} title={!sidebarOpen ? n.label : undefined}
            style={{ display:"flex", alignItems:"center", gap:"12px", padding:"10px 12px", borderRadius:"10px", border:"none", cursor:"pointer", fontFamily:"Inter,sans-serif", fontWeight:"600", fontSize:"13px", transition:"all 0.2s", background: tab===n.id ? "linear-gradient(135deg,rgba(99,102,241,0.25),rgba(6,182,212,0.1))" : "transparent", color: tab===n.id ? "var(--primary-light)" : "var(--text2)", borderLeft: tab===n.id ? "3px solid var(--primary)" : "3px solid transparent", whiteSpace:"nowrap" }}>
            <span style={{ fontSize:"17px", flexShrink:0 }}>{n.icon}</span>
            {sidebarOpen && n.label}
          </button>
        ))}
      </nav>

      {/* Bottom */}
      <div style={{ padding:"10px 8px", borderTop:"1px solid var(--border)", display:"flex", flexDirection:"column", gap:"2px" }}>
        <button onClick={toggleTheme} title={!sidebarOpen ? (theme==="dark"?"Light Mode":"Dark Mode") : undefined}
          style={{ display:"flex", alignItems:"center", gap:"12px", padding:"10px 12px", borderRadius:"10px", border:"none", cursor:"pointer", background:"transparent", color:"var(--text3)", fontFamily:"Inter,sans-serif", fontSize:"13px", whiteSpace:"nowrap" }}>
          <span style={{ fontSize:"17px" }}>{theme==="dark" ? "☀️" : "🌙"}</span>
          {sidebarOpen && (theme==="dark" ? "Light Mode" : "Dark Mode")}
        </button>
        <button onClick={() => setSidebarOpen(v => !v)}
          style={{ display:"flex", alignItems:"center", gap:"12px", padding:"10px 12px", borderRadius:"10px", border:"none", cursor:"pointer", background:"transparent", color:"var(--text3)", fontFamily:"Inter,sans-serif", fontSize:"13px", whiteSpace:"nowrap" }}>
          <span style={{ fontSize:"17px" }}>{sidebarOpen ? "◀" : "▶"}</span>
          {sidebarOpen && "Collapse"}
        </button>
        <button onClick={onLogout}
          style={{ display:"flex", alignItems:"center", gap:"12px", padding:"10px 12px", borderRadius:"10px", border:"none", cursor:"pointer", background:"transparent", color:"var(--danger)", fontFamily:"Inter,sans-serif", fontSize:"13px", fontWeight:"600", whiteSpace:"nowrap" }}>
          <span style={{ fontSize:"17px" }}>🚪</span>
          {sidebarOpen && "Logout"}
        </button>
      </div>
    </aside>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────
export default function Dashboard({ onLogout }) {
  const [tab, setTab]             = useState("analyze");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  return (
    <div style={{ display:"flex", minHeight:"100vh", background:"var(--bg)" }}>
      <Sidebar tab={tab} setTab={setTab} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} onLogout={onLogout} />
      <main style={{ flex:1, overflow:"auto", padding:"28px", minWidth:0 }}>
        {tab==="analyze"   && <AnalyzeTab />}
        {tab==="batch"     && <BatchTab />}
        {tab==="compare"   && <CompareTab />}
        {tab==="webcam"    && <WebcamTab />}
        {tab==="history"   && <HistoryTab />}
        {tab==="analytics" && <AnalyticsTab />}
        {tab==="insights"  && <InsightsTab />}
        {tab==="profile"   && <ProfileTab onLogout={onLogout} />}
      </main>
    </div>
  );
}

// ── ResultCard ────────────────────────────────────────────────────
function ResultCard({ result }) {
  const faces       = result.faces || [];
  const face        = faces[0] || {};
  const modelsReady = result.models_trained !== false;
  const emotion     = (face.emotion || "neutral").toLowerCase();
  const isSmiling   = face.smile === true;
  const smileProb   = face.smile_probability ?? face.smile_confidence ?? 0;
  const smilePct    = Math.round(smileProb * 100);
  const age         = face.age ?? face.age_prediction;
  const ageRange    = face.age_range || "";
  const smileData   = [{ name:"Smile", value: smilePct, fill: isSmiling ? "#10b981" : "#6366f1" }];
  const music       = face.music_recommendations || result.music_recommendations || [];

  return (
    <div className="fade-in" style={{ display:"flex", flexDirection:"column", gap:"12px" }}>
      {/* Badges */}
      <div style={{ display:"flex", gap:"8px", flexWrap:"wrap", alignItems:"center" }}>
        <span className="badge badge-info">👥 {result.num_faces} face{result.num_faces!==1?"s":""}</span>
        {result.processing_time && <span className="badge badge-cyan">⚡ {result.processing_time}s</span>}
        {!modelsReady && <span className="badge badge-warning">⚠️ Models not trained</span>}
      </div>

      {/* Age card */}
      <div className="card" style={{ display:"flex", alignItems:"center", gap:"16px", padding:"16px", background:"linear-gradient(135deg,rgba(99,102,241,0.08),rgba(6,182,212,0.05))" }}>
        <div style={{ width:"48px", height:"48px", background:"linear-gradient(135deg,#6366f1,#06b6d4)", borderRadius:"14px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"22px", flexShrink:0, boxShadow:"0 4px 16px rgba(99,102,241,0.4)" }}>🎂</div>
        <div style={{ flex:1 }}>
          <p style={{ color:"var(--text3)", fontSize:"10px", fontWeight:"700", letterSpacing:"0.1em", marginBottom:"2px" }}>PREDICTED AGE</p>
          {age!=null
            ? <><p style={{ fontSize:"36px", fontWeight:"900", lineHeight:1 }} className="gradient-text">{age}</p>
                {ageRange && <p style={{ color:"var(--text3)", fontSize:"11px", marginTop:"2px" }}>Range: {ageRange}</p>}</>
            : <p style={{ color:"var(--text3)" }}>— model not trained</p>}
        </div>
      </div>

      {/* Smile card */}
      <div className="card" style={{ display:"flex", alignItems:"center", gap:"16px", padding:"16px" }}>
        <div style={{ width:"72px", height:"72px", flexShrink:0 }}>
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart cx="50%" cy="50%" innerRadius="55%" outerRadius="100%" data={smileData} startAngle={90} endAngle={-270}>
              <RadialBar dataKey="value" cornerRadius={6} background={{ fill:"var(--bg2)" }} />
            </RadialBarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <p style={{ color:"var(--text3)", fontSize:"10px", fontWeight:"700", letterSpacing:"0.1em", marginBottom:"2px" }}>SMILE SCORE</p>
          <p style={{ fontSize:"30px", fontWeight:"900", color: isSmiling ? "var(--success)" : "var(--primary-light)", lineHeight:1 }}>{smilePct}%</p>
          <span className={`badge ${isSmiling?"badge-success":"badge-info"}`} style={{ marginTop:"4px" }}>{isSmiling?"😊 Smiling":"😐 Not smiling"}</span>
        </div>
      </div>

      {/* Emotion card */}
      <div className="card" style={{ display:"flex", alignItems:"center", gap:"16px", padding:"16px", background: EMOTION_BG[emotion] || "var(--card)" }}>
        <div style={{ width:"48px", height:"48px", background:`${EMOTION_COLOR[emotion]||"#6366f1"}22`, border:`2px solid ${EMOTION_COLOR[emotion]||"#6366f1"}`, borderRadius:"14px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"24px", flexShrink:0 }}>
          {EMOTION_EMOJI[emotion]||"😐"}
        </div>
        <div style={{ flex:1 }}>
          <p style={{ color:"var(--text3)", fontSize:"10px", fontWeight:"700", letterSpacing:"0.1em", marginBottom:"2px" }}>EMOTION</p>
          {emotion!=="unknown"
            ? <><p style={{ fontSize:"22px", fontWeight:"800", color:EMOTION_COLOR[emotion]||"var(--text)", textTransform:"capitalize", lineHeight:1 }}>{emotion}</p>
                {face.emotion_confidence>0 && (
                  <div style={{ marginTop:"6px" }}>
                    <div className="progress-bar" style={{ width:"100px" }}>
                      <div className="progress-fill" style={{ width:`${Math.round(face.emotion_confidence*100)}%`, background:EMOTION_COLOR[emotion] }} />
                    </div>
                    <p style={{ color:"var(--text3)", fontSize:"10px", marginTop:"2px" }}>{Math.round(face.emotion_confidence*100)}% confidence</p>
                  </div>
                )}</>
            : <p style={{ color:"var(--text3)" }}>— model not trained</p>}
        </div>
      </div>

      {/* Music recommendations */}
      <MusicCard tracks={music} emotion={face.emotion} />
    </div>
  );
}

// ── MusicCard ─────────────────────────────────────────────────────
function MusicCard({ tracks, emotion }) {
  const [expanded, setExpanded] = useState(false);
  if (!tracks || tracks.length === 0) return null;
  const emotion_lc = (emotion || "neutral").toLowerCase();
  const color = EMOTION_COLOR[emotion_lc] || "#6366f1";
  const shown = expanded ? tracks : tracks.slice(0, 3);
  return (
    <div className="card fade-in" style={{ padding:"16px", borderLeft:`3px solid ${color}`, marginTop:"4px" }}>
      <div style={{ display:"flex", alignItems:"center", gap:"10px", marginBottom:"12px" }}>
        <span style={{ fontSize:"20px" }}>🎵</span>
        <p style={{ fontWeight:"700", fontSize:"13px", color }}>Music for your mood</p>
        <span className="badge" style={{ background:`${color}22`, color, marginLeft:"auto", fontSize:"10px" }}>
          {(emotion || "Neutral").charAt(0).toUpperCase() + (emotion || "Neutral").slice(1)}
        </span>
      </div>
      <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
        {shown.map((t, i) => (
          <a key={i} href={t.spotify} target="_blank" rel="noopener noreferrer"
            style={{ display:"flex", alignItems:"center", gap:"12px", padding:"10px 12px", borderRadius:"10px", background:"var(--bg2)", border:"1px solid var(--border2)", textDecoration:"none", transition:"all 0.2s" }}
            onMouseEnter={e => e.currentTarget.style.borderColor = color}
            onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border2)"}>
            <div style={{ width:"36px", height:"36px", background:`${color}22`, borderRadius:"8px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"16px", flexShrink:0 }}>🎧</div>
            <div style={{ flex:1, minWidth:0 }}>
              <p style={{ fontWeight:"700", fontSize:"12px", color:"var(--text)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{t.title}</p>
              <p style={{ fontSize:"11px", color:"var(--text3)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{t.artist}</p>
            </div>
            <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:"3px", flexShrink:0 }}>
              <span style={{ fontSize:"10px", background:`${color}22`, color, padding:"2px 6px", borderRadius:"4px", fontWeight:"600" }}>{t.genre}</span>
              <span style={{ fontSize:"10px", color:"var(--text3)" }}>{t.mood}</span>
            </div>
          </a>
        ))}
      </div>
      {tracks.length > 3 && (
        <button onClick={() => setExpanded(v => !v)}
          style={{ marginTop:"8px", background:"none", border:"none", cursor:"pointer", color, fontSize:"12px", fontWeight:"600", padding:"4px 0" }}>
          {expanded ? "▲ Show less" : `▼ Show ${tracks.length - 3} more`}
        </button>
      )}
    </div>
  );
}

// ── FaceCard ──────────────────────────────────────────────────────
function FaceCard({ face }) {
  const emotion   = (face.emotion||"neutral").toLowerCase();
  const smileProb = face.smile_probability ?? face.smile_confidence ?? 0;
  const smilePct  = Math.round(smileProb * 100);
  const isSmiling = face.smile === true;
  return (
    <div className="card card-hover" style={{ padding:"16px" }}>
      <div style={{ display:"flex", alignItems:"center", gap:"10px", marginBottom:"12px" }}>
        <div style={{ width:"34px", height:"34px", background:EMOTION_BG[emotion]||"rgba(99,102,241,0.12)", border:`1.5px solid ${EMOTION_COLOR[emotion]||"#6366f1"}`, borderRadius:"10px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"16px" }}>
          {EMOTION_EMOJI[emotion]||"😐"}
        </div>
        <span style={{ fontWeight:"700", fontSize:"13px" }}>Face #{face.face_id}</span>
      </div>
      <div style={{ display:"flex", flexDirection:"column", gap:"6px" }}>
        <Row label="Age"     value={face.age!=null ? `${face.age} (${face.age_range})` : "—"} />
        <Row label="Smile"   value={`${smilePct}%`} color={isSmiling?"var(--success)":undefined} />
        <Row label="Emotion" value={face.emotion||"—"} color={EMOTION_COLOR[emotion]} />
        <Row label="Confidence" value={`${Math.round((face.emotion_confidence||0)*100)}%`} />
      </div>
    </div>
  );
}

// ── ANALYZE TAB ───────────────────────────────────────────────────
function AnalyzeTab() {
  const [preview, setPreview] = useState(null);
  const [file, setFile]       = useState(null);
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);

  const onDrop = useCallback((files) => {
    const f = files[0]; if (!f) return;
    setFile(f); setResult(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept:{"image/*":[]}, multiple:false });

  const analyze = async () => {
    if (!file) { toast.warning("Please upload an image first"); return; }
    setLoading(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await axios.post(`${API}/api/prediction/analyze`, fd, { headers:{...authHdr(),"Content-Type":"multipart/form-data"} });
      setResult(res.data); toast.success("Analysis complete!");
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      if (err.response?.status===401) { toast.error("Session expired"); setTimeout(()=>{localStorage.clear();window.dispatchEvent(new Event("auth-change"));},1500); }
      else toast.error(`Analysis failed: ${detail}`);
    }
    setLoading(false);
  };

  const downloadReport = async () => {
    if (!result?.prediction_id) return;
    try {
      const res = await axios.post(`${API}/api/reports/generate`, { prediction_id:result.prediction_id }, { headers:authHdr(), responseType:"blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href=url; a.download=`report_${result.prediction_id}.pdf`; a.click();
      window.URL.revokeObjectURL(url); toast.success("Report downloaded!");
    } catch { toast.error("Report generation failed"); }
  };

  return (
    <div className="fade-in">
      <PageHeader title={<>Face Analysis <span className="gradient-text">Studio</span></>} subtitle="Upload a photo to detect age, smile & emotion in real-time" />
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"24px" }}>
        {/* Upload */}
        <div>
          <div {...getRootProps()} style={{ border:`2px dashed ${isDragActive?"var(--primary)":"var(--border)"}`, borderRadius:"16px", padding:"28px", textAlign:"center", cursor:"pointer", background: isDragActive?"rgba(99,102,241,0.08)":"var(--card)", transition:"all 0.2s", minHeight:"260px", display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center" }}>
            <input {...getInputProps()} />
            {preview
              ? <img src={preview} alt="preview" style={{ maxWidth:"100%", maxHeight:"220px", borderRadius:"12px", objectFit:"contain" }} />
              : <><div style={{ fontSize:"48px", marginBottom:"12px" }}>📸</div>
                  <p style={{ fontWeight:"700", marginBottom:"6px" }}>{isDragActive?"Drop it here!":"Drag & drop an image"}</p>
                  <p style={{ color:"var(--text3)", fontSize:"13px" }}>or click to browse · JPG, PNG, WEBP</p>
                  <div style={{ display:"flex", gap:"6px", marginTop:"12px", flexWrap:"wrap", justifyContent:"center" }}>
                    {["JPG","PNG","WEBP"].map(f=><span key={f} className="badge badge-info">{f}</span>)}
                  </div></>}
          </div>
          <div style={{ display:"flex", gap:"10px", marginTop:"12px" }}>
            <button className="btn btn-primary" onClick={analyze} disabled={loading||!file} style={{ flex:1, justifyContent:"center" }}>
              {loading ? "⚡ Analyzing..." : "⚡ Analyze Now"}
            </button>
            {preview && <button className="btn btn-secondary" onClick={()=>{setPreview(null);setFile(null);setResult(null);}}>✕</button>}
            {result && <button className="btn btn-success" onClick={downloadReport}>📄 PDF</button>}
          </div>
        </div>

        {/* Results */}
        <div>
          {!result && !loading && (
            <div className="card" style={{ height:"100%", display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", minHeight:"260px" }}>
              <div style={{ fontSize:"48px", marginBottom:"12px", opacity:0.2 }}>🎯</div>
              <p style={{ color:"var(--text3)", fontSize:"14px" }}>Results will appear here</p>
            </div>
          )}
          {loading && (
            <div className="card" style={{ height:"100%", display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", minHeight:"260px" }}>
              <div style={{ fontSize:"48px", marginBottom:"12px" }} className="pulse">🔍</div>
              <p style={{ color:"var(--text2)", fontWeight:"600" }}>Running AI models...</p>
              <p style={{ color:"var(--text3)", fontSize:"12px", marginTop:"6px" }}>Age · Smile · Emotion</p>
            </div>
          )}
          {result && <ResultCard result={result} />}
        </div>
      </div>

      {/* Multi-face grid */}
      {result?.faces?.length > 1 && (
        <div style={{ marginTop:"28px" }}>
          <h3 style={{ fontWeight:"700", marginBottom:"14px" }}>All {result.faces.length} Faces Detected</h3>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:"12px" }}>
            {result.faces.map(face => <FaceCard key={face.face_id} face={face} />)}
          </div>
        </div>
      )}
    </div>
  );
}

// ── BATCH UPLOAD TAB ──────────────────────────────────────────────
function BatchTab() {
  const [files, setFiles]     = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback((dropped) => {
    setFiles(prev => [...prev, ...dropped].slice(0, 10));
    setResults([]);
  }, []);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept:{"image/*":[]}, multiple:true });

  const analyze = async () => {
    if (!files.length) { toast.warning("Add at least one image"); return; }
    setLoading(true); setProgress(0);
    try {
      const fd = new FormData();
      files.forEach(f => fd.append("files", f));
      const res = await axios.post(`${API}/api/prediction/batch-analyze`, fd, {
        headers:{...authHdr(),"Content-Type":"multipart/form-data"},
        onUploadProgress: e => setProgress(Math.round(e.loaded/e.total*50)),
      });
      setProgress(100);
      setResults(res.data.batch_results || []);
      toast.success(`Analyzed ${res.data.total} images!`);
    } catch (err) {
      toast.error(`Batch failed: ${err.response?.data?.detail||err.message}`);
    }
    setLoading(false);
  };

  const summary = results.filter(r=>!r.error);
  const totalFaces = summary.reduce((s,r)=>s+(r.num_faces||0),0);
  const avgAge = summary.length ? Math.round(summary.reduce((s,r)=>{
    const ages = (r.faces||[]).map(f=>f.age).filter(Boolean);
    return s + (ages.length ? ages.reduce((a,b)=>a+b,0)/ages.length : 0);
  },0)/summary.length) : 0;

  return (
    <div className="fade-in">
      <PageHeader title={<>Batch <span className="gradient-text">Analysis</span></>} subtitle="Analyze up to 10 images at once" />

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"24px", marginBottom:"24px" }}>
        <div>
          <div {...getRootProps()} style={{ border:`2px dashed ${isDragActive?"var(--primary)":"var(--border)"}`, borderRadius:"16px", padding:"28px", textAlign:"center", cursor:"pointer", background: isDragActive?"rgba(99,102,241,0.08)":"var(--card)", minHeight:"180px", display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center" }}>
            <input {...getInputProps()} />
            <div style={{ fontSize:"40px", marginBottom:"10px" }}>📦</div>
            <p style={{ fontWeight:"700", marginBottom:"4px" }}>{isDragActive?"Drop files here!":"Drop multiple images"}</p>
            <p style={{ color:"var(--text3)", fontSize:"13px" }}>Up to 10 images · JPG, PNG, WEBP</p>
          </div>
          <div style={{ display:"flex", gap:"10px", marginTop:"12px" }}>
            <button className="btn btn-primary" onClick={analyze} disabled={loading||!files.length} style={{ flex:1, justifyContent:"center" }}>
              {loading ? `⚡ Analyzing... ${progress}%` : `⚡ Analyze ${files.length} Image${files.length!==1?"s":""}`}
            </button>
            {files.length>0 && <button className="btn btn-secondary" onClick={()=>{setFiles([]);setResults([]);}}>✕ Clear</button>}
          </div>
          {loading && (
            <div style={{ marginTop:"10px" }}>
              <div className="progress-bar"><div className="progress-fill" style={{ width:`${progress}%` }} /></div>
            </div>
          )}
        </div>

        {/* File list */}
        <div className="card" style={{ padding:"16px", maxHeight:"260px", overflowY:"auto" }}>
          <p style={{ fontWeight:"700", marginBottom:"12px", fontSize:"13px" }}>Selected Files ({files.length}/10)</p>
          {files.length===0 && <p style={{ color:"var(--text3)", fontSize:"13px" }}>No files selected</p>}
          {files.map((f,i)=>(
            <div key={i} style={{ display:"flex", alignItems:"center", gap:"10px", padding:"8px 0", borderBottom:"1px solid var(--border2)" }}>
              <span style={{ fontSize:"20px" }}>🖼️</span>
              <div style={{ flex:1, minWidth:0 }}>
                <p style={{ fontSize:"12px", fontWeight:"600", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{f.name}</p>
                <p style={{ fontSize:"11px", color:"var(--text3)" }}>{(f.size/1024).toFixed(1)} KB</p>
              </div>
              <button onClick={()=>setFiles(prev=>prev.filter((_,j)=>j!==i))} style={{ background:"none", border:"none", cursor:"pointer", color:"var(--danger)", fontSize:"16px" }}>✕</button>
            </div>
          ))}
        </div>
      </div>

      {/* Batch summary */}
      {results.length>0 && (
        <>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:"14px", marginBottom:"20px" }}>
            {[
              { label:"Images Analyzed", value:summary.length, icon:"🖼️", color:"#6366f1" },
              { label:"Total Faces",     value:totalFaces,      icon:"👥", color:"#10b981" },
              { label:"Avg Age",         value:avgAge||"—",     icon:"🎂", color:"#f59e0b" },
            ].map(s=>(
              <div key={s.label} className="stat-card">
                <div style={{ fontSize:"24px" }}>{s.icon}</div>
                <p style={{ fontSize:"28px", fontWeight:"900", color:s.color, lineHeight:1 }}>{s.value}</p>
                <p style={{ fontSize:"12px", color:"var(--text3)" }}>{s.label}</p>
              </div>
            ))}
          </div>

          <div style={{ display:"flex", flexDirection:"column", gap:"10px" }}>
            {results.map((r,i)=>(
              <div key={i} className="card card-hover" style={{ padding:"14px 18px" }}>
                {r.error
                  ? <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
                      <span style={{ fontSize:"20px" }}>❌</span>
                      <div><p style={{ fontWeight:"600", fontSize:"13px" }}>{r.filename}</p><p style={{ color:"var(--danger)", fontSize:"12px" }}>{r.error}</p></div>
                    </div>
                  : <div style={{ display:"flex", alignItems:"center", gap:"16px" }}>
                      <span style={{ fontSize:"24px" }}>✅</span>
                      <div style={{ flex:1 }}>
                        <p style={{ fontWeight:"700", fontSize:"13px", marginBottom:"6px" }}>{r.filename}</p>
                        <div style={{ display:"flex", gap:"8px", flexWrap:"wrap" }}>
                          <span className="badge badge-info">👥 {r.num_faces} face{r.num_faces!==1?"s":""}</span>
                          {r.faces?.slice(0,3).map(f=>(
                            <span key={f.face_id} className="badge" style={{ background:EMOTION_BG[(f.emotion||"").toLowerCase()]||"rgba(99,102,241,0.12)", color:EMOTION_COLOR[(f.emotion||"").toLowerCase()]||"var(--text)" }}>
                              {EMOTION_EMOJI[(f.emotion||"").toLowerCase()]||"😐"} {f.age}y
                            </span>
                          ))}
                          <span className="badge badge-cyan">⚡ {r.processing_time}s</span>
                        </div>
                      </div>
                    </div>}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── PHOTO PANEL (used by CompareTab) ─────────────────────────────
function PhotoPanel({ side, preview, result, inputRef, onPickFile, onClear }) {
  const label = side === "left" ? "Photo A" : "Photo B";

  const onDragOver = (e) => e.preventDefault();
  const onDrop     = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("image/")) onPickFile(side, f);
  };

  return (
    <div style={{ flex:1 }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:"10px" }}>
        <p style={{ fontWeight:"700", fontSize:"14px", color:"var(--text2)" }}>{label}</p>
        {preview && (
          <button className="btn btn-secondary" style={{ padding:"4px 10px", fontSize:"11px" }}
            onClick={() => onClear(side)}>✕ Clear</button>
        )}
      </div>

      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={onDragOver} onDrop={onDrop}
        style={{ border:"2px dashed var(--border)", borderRadius:"16px", minHeight:"240px", display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", cursor:"pointer", background:"var(--card)", overflow:"hidden", transition:"all 0.2s", position:"relative" }}
        onMouseEnter={e => e.currentTarget.style.borderColor = "var(--primary)"}
        onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          style={{ display:"none" }}
          onChange={e => onPickFile(side, e.target.files[0])}
        />
        {preview ? (
          <img src={preview} alt={label} style={{ width:"100%", height:"240px", objectFit:"cover", display:"block" }} />
        ) : (
          <div style={{ textAlign:"center", padding:"28px" }}>
            <div style={{ fontSize:"52px", marginBottom:"14px", opacity:0.5 }}>📸</div>
            <p style={{ fontWeight:"700", fontSize:"15px", marginBottom:"6px" }}>Click to select image</p>
            <p style={{ color:"var(--text3)", fontSize:"12px", marginBottom:"14px" }}>or drag & drop here</p>
            <div style={{ display:"flex", gap:"6px", justifyContent:"center" }}>
              {["JPG","PNG","WEBP"].map(f => <span key={f} className="badge badge-info">{f}</span>)}
            </div>
          </div>
        )}
      </div>

      {result && result.faces?.length > 0 && (() => {
        const face = result.faces[0];
        const em   = (face.emotion||"neutral").toLowerCase();
        const sp   = Math.round((face.smile_probability??face.smile_confidence??0)*100);
        return (
          <div className="card fade-in" style={{ marginTop:"10px", padding:"14px" }}>
            <div style={{ display:"flex", gap:"8px", flexWrap:"wrap", marginBottom:"8px" }}>
              <span className="badge badge-info">👥 {result.num_faces} face{result.num_faces!==1?"s":""}</span>
              <span className="badge badge-cyan">🎂 {face.age??"—"} yrs</span>
              <span className={`badge ${face.smile?"badge-success":"badge-info"}`}>😊 {sp}%</span>
              <span className="badge" style={{ background:EMOTION_BG[em]||"rgba(99,102,241,0.12)", color:EMOTION_COLOR[em]||"var(--text)" }}>
                {EMOTION_EMOJI[em]||"😐"} {face.emotion}
              </span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width:`${sp}%`, background:EMOTION_COLOR[em]||"var(--primary)" }} />
            </div>
          </div>
        );
      })()}
    </div>
  );
}

// ── COMPARE TAB ───────────────────────────────────────────────────
function CompareTab() {
  const [leftFile, setLeftFile]         = useState(null);
  const [rightFile, setRightFile]       = useState(null);
  const [leftPreview, setLeftPreview]   = useState(null);
  const [rightPreview, setRightPreview] = useState(null);
  const [leftResult, setLeftResult]     = useState(null);
  const [rightResult, setRightResult]   = useState(null);
  const [loading, setLoading]           = useState(false);

  const leftInputRef  = useRef(null);
  const rightInputRef = useRef(null);

  const pickFile = (side, file) => {
    if (!file) return;
    if (side === "left") { setLeftFile(file); setLeftResult(null); }
    else                 { setRightFile(file); setRightResult(null); }
    const reader = new FileReader();
    reader.onload = (e) => {
      if (side === "left") setLeftPreview(e.target.result);
      else                 setRightPreview(e.target.result);
    };
    reader.readAsDataURL(file);
  };

  const clearSide = (side) => {
    if (side === "left") { setLeftFile(null); setLeftPreview(null); setLeftResult(null); }
    else                 { setRightFile(null); setRightPreview(null); setRightResult(null); }
  };

  const analyzeOne = async (file) => {
    const fd = new FormData(); fd.append("file", file);
    const res = await axios.post(`${API}/api/prediction/analyze`, fd, { headers:{...authHdr(),"Content-Type":"multipart/form-data"} });
    return res.data;
  };

  const compare = async () => {
    if (!leftFile || !rightFile) { toast.warning("Select both images to compare"); return; }
    setLoading(true);
    try {
      const [l, r] = await Promise.all([analyzeOne(leftFile), analyzeOne(rightFile)]);
      setLeftResult(l); setRightResult(r);
      toast.success("Comparison complete!");
    } catch (err) {
      toast.error(`Compare failed: ${err.response?.data?.detail||err.message}`);
    }
    setLoading(false);
  };

  const showDiff = leftResult?.faces?.[0] && rightResult?.faces?.[0];
  const lf = leftResult?.faces?.[0]  || {};
  const rf = rightResult?.faces?.[0] || {};

  return (
    <div className="fade-in">
      <PageHeader title={<>Face <span className="gradient-text">Comparison</span></>} subtitle="Select two photos to compare age, smile & emotion side by side" />

      <div style={{ display:"grid", gridTemplateColumns:"1fr 48px 1fr", gap:"16px", alignItems:"start", marginBottom:"20px" }}>
        <PhotoPanel side="left"  preview={leftPreview}  result={leftResult}  inputRef={leftInputRef}  onPickFile={pickFile} onClear={clearSide} />
        <div style={{ display:"flex", alignItems:"center", justifyContent:"center", paddingTop:"120px" }}>
          <div style={{ width:"44px", height:"44px", background:"linear-gradient(135deg,var(--primary),var(--secondary))", borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"18px", boxShadow:"var(--glow)", flexShrink:0 }}>⚖️</div>
        </div>
        <PhotoPanel side="right" preview={rightPreview} result={rightResult} inputRef={rightInputRef} onPickFile={pickFile} onClear={clearSide} />
      </div>

      <div style={{ display:"flex", justifyContent:"center", marginBottom:"24px" }}>
        <button className="btn btn-primary" onClick={compare} disabled={loading||!leftFile||!rightFile} style={{ padding:"12px 48px", fontSize:"15px" }}>
          {loading ? "⚡ Comparing..." : "⚡ Compare Now"}
        </button>
      </div>

      {showDiff && (
        <div className="card fade-in" style={{ padding:"24px" }}>
          <h3 style={{ fontWeight:"700", marginBottom:"20px", fontSize:"16px" }}>📊 Comparison Results</h3>
          <div style={{ display:"grid", gridTemplateColumns:"1fr auto 1fr", gap:"16px", alignItems:"center" }}>
            {[
              { label:"Age",        a: lf.age??"-",  b: rf.age??"-",  winner: lf.age && rf.age ? (lf.age < rf.age ? "A" : "B") : null },
              { label:"Smile %",    a:`${Math.round((lf.smile_probability??0)*100)}%`, b:`${Math.round((rf.smile_probability??0)*100)}%`, winner:(lf.smile_probability??0)>(rf.smile_probability??0)?"A":"B" },
              { label:"Emotion",    a:lf.emotion||"—", b:rf.emotion||"—", winner:null },
              { label:"Confidence", a:`${Math.round((lf.emotion_confidence??0)*100)}%`, b:`${Math.round((rf.emotion_confidence??0)*100)}%`, winner:(lf.emotion_confidence??0)>(rf.emotion_confidence??0)?"A":"B" },
            ].map(row => (
              <React.Fragment key={row.label}>
                <div className="card" style={{ padding:"12px 16px", textAlign:"center", border: row.winner==="A"?"2px solid var(--success)":"1px solid var(--border)" }}>
                  <p style={{ color:"var(--text3)", fontSize:"11px", marginBottom:"4px" }}>Photo A</p>
                  <p style={{ fontWeight:"800", fontSize:"18px" }}>{row.a}</p>
                  {row.winner==="A" && <span className="badge badge-success" style={{ marginTop:"4px" }}>Winner</span>}
                </div>
                <div style={{ textAlign:"center" }}>
                  <p style={{ color:"var(--text3)", fontSize:"11px", fontWeight:"700" }}>{row.label}</p>
                </div>
                <div className="card" style={{ padding:"12px 16px", textAlign:"center", border: row.winner==="B"?"2px solid var(--success)":"1px solid var(--border)" }}>
                  <p style={{ color:"var(--text3)", fontSize:"11px", marginBottom:"4px" }}>Photo B</p>
                  <p style={{ fontWeight:"800", fontSize:"18px" }}>{row.b}</p>
                  {row.winner==="B" && <span className="badge badge-success" style={{ marginTop:"4px" }}>Winner</span>}
                </div>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── WEBCAM TAB (with Live Continuous Analysis) ────────────────────
function WebcamTab() {
  const videoRef    = useRef(null);
  const canvasRef   = useRef(null);
  const intervalRef = useRef(null);
  const [active, setActive]       = useState(false);
  const [captured, setCaptured]   = useState(null);
  const [result, setResult]       = useState(null);
  const [loading, setLoading]     = useState(false);
  const [liveMode, setLiveMode]   = useState(false);
  const [liveResult, setLiveResult] = useState(null);
  const [frameCount, setFrameCount] = useState(0);
  const streamRef = useRef(null);

  const startCam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video:{ width:640, height:480 } });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setActive(true);
    } catch { toast.error("Camera access denied"); }
  };

  const stopCam = useCallback(() => {
    stopLive();
    if (streamRef.current) streamRef.current.getTracks().forEach(t=>t.stop());
    setActive(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => () => stopCam(), [stopCam]);

  const capture = () => {
    const video=videoRef.current, canvas=canvasRef.current;
    if (!video||!canvas) return;
    canvas.width=video.videoWidth; canvas.height=video.videoHeight;
    canvas.getContext("2d").drawImage(video,0,0);
    setCaptured(canvas.toDataURL("image/jpeg",0.9)); setResult(null);
  };

  const analyzeCapture = async (dataUrl) => {
    const src = dataUrl || captured; if (!src) return;
    setLoading(true);
    try {
      const blob = await (await fetch(src)).blob();
      const fd = new FormData(); fd.append("file", blob, "webcam.jpg");
      const res = await axios.post(`${API}/api/prediction/analyze`, fd, { headers:{...authHdr(),"Content-Type":"multipart/form-data"} });
      if (dataUrl) setLiveResult(res.data);
      else { setResult(res.data); toast.success("Analysis complete!"); }
    } catch (err) {
      if (!dataUrl) toast.error(`Analysis failed: ${err.response?.data?.detail||err.message}`);
    }
    setLoading(false);
  };

  const startLive = () => {
    setLiveMode(true);
    intervalRef.current = setInterval(async () => {
      const video=videoRef.current, canvas=canvasRef.current;
      if (!video||!canvas||!active) return;
      canvas.width=video.videoWidth; canvas.height=video.videoHeight;
      canvas.getContext("2d").drawImage(video,0,0);
      const dataUrl = canvas.toDataURL("image/jpeg",0.7);
      setFrameCount(c=>c+1);
      await analyzeCapture(dataUrl);
    }, 3000);
  };

  const stopLive = () => {
    setLiveMode(false);
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current=null; }
  };

  const liveEmotion = (liveResult?.faces?.[0]?.emotion||"neutral").toLowerCase();
  const liveSmile   = Math.round((liveResult?.faces?.[0]?.smile_probability??0)*100);

  return (
    <div className="fade-in">
      <PageHeader title={<>Live Webcam <span className="gradient-text">Analysis</span></>} subtitle="Real-time face analysis — auto-analyzes every 3 seconds in live mode" />

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"24px" }}>
        <div>
          <div style={{ background:"var(--card)", border:"1px solid var(--border)", borderRadius:"16px", overflow:"hidden", aspectRatio:"4/3", display:"flex", alignItems:"center", justifyContent:"center", position:"relative" }}>
            <video ref={videoRef} autoPlay playsInline muted style={{ width:"100%", height:"100%", objectFit:"cover", display:active?"block":"none" }} />
            <canvas ref={canvasRef} style={{ display:"none" }} />
            {!active && <div style={{ textAlign:"center" }}><div style={{ fontSize:"48px", marginBottom:"10px", opacity:0.3 }}>📷</div><p style={{ color:"var(--text3)" }}>Camera is off</p></div>}
            {active && (
              <div style={{ position:"absolute", top:"10px", right:"10px", display:"flex", gap:"6px" }}>
                <span className="badge badge-danger" style={{ animation:"pulse 1.5s infinite" }}>● LIVE</span>
                {liveMode && <span className="badge badge-success">🤖 AUTO</span>}
              </div>
            )}
            {/* Live overlay */}
            {liveMode && liveResult?.faces?.[0] && (
              <div style={{ position:"absolute", bottom:"10px", left:"10px", right:"10px", background:"rgba(0,0,0,0.7)", backdropFilter:"blur(8px)", borderRadius:"10px", padding:"10px 14px", display:"flex", gap:"12px", alignItems:"center" }}>
                <span style={{ fontSize:"24px" }}>{EMOTION_EMOJI[liveEmotion]||"😐"}</span>
                <div>
                  <p style={{ fontWeight:"700", fontSize:"13px", color:EMOTION_COLOR[liveEmotion]||"#fff" }}>{liveResult.faces[0].emotion} · Age {liveResult.faces[0].age}</p>
                  <p style={{ fontSize:"11px", color:"rgba(255,255,255,0.6)" }}>Smile: {liveSmile}% · Frame #{frameCount}</p>
                </div>
              </div>
            )}
          </div>

          <div style={{ display:"flex", gap:"8px", marginTop:"12px", flexWrap:"wrap" }}>
            {!active
              ? <button className="btn btn-primary" onClick={startCam} style={{ flex:1, justifyContent:"center" }}>📷 Start Camera</button>
              : <>
                  <button className="btn btn-success" onClick={capture} style={{ flex:1, justifyContent:"center" }}>📸 Capture</button>
                  {!liveMode
                    ? <button className="btn btn-secondary" onClick={startLive} style={{ flex:1, justifyContent:"center" }}>🤖 Live Mode</button>
                    : <button className="btn btn-warning" onClick={stopLive} style={{ flex:1, justifyContent:"center", background:"rgba(245,158,11,0.15)", color:"var(--warning)", border:"1px solid rgba(245,158,11,0.3)" }}>⏹ Stop Live</button>}
                  <button className="btn btn-danger" onClick={stopCam}>⏹</button>
                </>}
          </div>
          {liveMode && <p style={{ color:"var(--text3)", fontSize:"12px", marginTop:"8px", textAlign:"center" }}>🤖 Auto-analyzing every 3 seconds · {frameCount} frames processed</p>}
        </div>

        <div>
          {captured && (
            <div style={{ display:"flex", flexDirection:"column", gap:"12px" }}>
              <div style={{ background:"var(--card)", border:"1px solid var(--border)", borderRadius:"14px", overflow:"hidden" }}>
                <img src={captured} alt="captured" style={{ width:"100%", display:"block" }} />
              </div>
              <div style={{ display:"flex", gap:"10px" }}>
                <button className="btn btn-primary" onClick={()=>analyzeCapture(null)} disabled={loading} style={{ flex:1, justifyContent:"center" }}>
                  {loading?"⚡ Analyzing...":"⚡ Analyze Capture"}
                </button>
                <button className="btn btn-secondary" onClick={()=>{setCaptured(null);setResult(null);}}>✕</button>
              </div>
              {result && <ResultCard result={result} />}
            </div>
          )}
          {!captured && liveMode && liveResult && <ResultCard result={liveResult} />}
          {!captured && !liveMode && (
            <div className="card" style={{ height:"100%", display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", minHeight:"260px" }}>
              <div style={{ fontSize:"48px", marginBottom:"12px", opacity:0.2 }}>📸</div>
              <p style={{ color:"var(--text3)" }}>Capture a frame or enable Live Mode</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── HISTORY TAB ───────────────────────────────────────────────────
function HistoryTab() {
  const [history, setHistory]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [search, setSearch]     = useState("");
  const [deleting, setDeleting] = useState(null);
  const [thumbs, setThumbs]     = useState({});  // id -> objectURL

  const load = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/api/prediction/history?limit=100`, { headers:authHdr() });
      const items = res.data.predictions || res.data || [];
      setHistory(items);
      // Fetch thumbnails with auth
      items.forEach(async (item) => {
        if (!item.id || !item.image_url) return;
        try {
          const imgRes = await axios.get(`${API}${item.image_url}`, { headers:authHdr(), responseType:"blob" });
          const url = URL.createObjectURL(imgRes.data);
          setThumbs(prev => ({ ...prev, [item.id]: url }));
        } catch { /* image not available, fallback to emoji */ }
      });
    } catch { toast.error("Failed to load history"); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const filtered = history.filter(item => {
    const q = search.toLowerCase();
    return !q || (item.dominant_emotion||"").toLowerCase().includes(q) || String(Math.round(item.avg_age||0)).includes(q);
  });

  const downloadReport = async (predId) => {
    try {
      const res = await axios.post(`${API}/api/reports/generate`, { prediction_id:predId }, { headers:authHdr(), responseType:"blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href=url; a.download=`report_${predId}.pdf`; a.click();
      window.URL.revokeObjectURL(url); toast.success("Report downloaded!");
    } catch { toast.error("Report generation failed"); }
  };

  const deleteItem = async (id) => {
    setDeleting(id);
    try {
      await axios.delete(`${API}/api/prediction/history/${id}`, { headers:authHdr() });
      setHistory(prev => prev.filter(h=>h.id!==id)); toast.success("Deleted");
    } catch { toast.error("Delete failed"); }
    setDeleting(null);
  };

  const exportCSV = async () => {
    try {
      const res = await axios.get(`${API}/api/prediction/export-csv`, { headers:authHdr(), responseType:"blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a"); a.href=url; a.download="analysis_history.csv"; a.click();
      window.URL.revokeObjectURL(url); toast.success("CSV exported!");
    } catch { toast.error("Export failed"); }
  };

  return (
    <div className="fade-in">
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:"24px", flexWrap:"wrap", gap:"12px" }}>
        <PageHeader title={<>Prediction <span className="gradient-text">History</span></>} subtitle={`${history.length} total analyses`} noMargin />
        <div style={{ display:"flex", gap:"8px", flexWrap:"wrap" }}>
          <input placeholder="🔍 Search emotion, age..." value={search} onChange={e=>setSearch(e.target.value)} style={{ width:"200px" }} />
          <button className="btn btn-secondary" onClick={load}>🔄</button>
          <button className="btn btn-success" onClick={exportCSV} title="Export as CSV">📊 CSV</button>
        </div>
      </div>

      {loading && <LoadingState text="Loading history..." />}

      {!loading && filtered.length===0 && (
        <div className="card" style={{ textAlign:"center", padding:"60px" }}>
          <div style={{ fontSize:"48px", marginBottom:"14px" }}>📭</div>
          <p style={{ color:"var(--text2)" }}>{search?"No results match your search":"No predictions yet. Go analyze an image!"}</p>
        </div>
      )}

      <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
        {filtered.map((item,i) => {
          const emotion  = (item.dominant_emotion||"neutral").toLowerCase();
          const smilePct = item.num_faces>0 ? Math.round((item.smile_count/item.num_faces)*100) : 0;
          const avgAge   = item.avg_age!=null ? Math.round(item.avg_age) : "—";
          const thumbUrl = thumbs[item.id] || null;
          return (
            <div key={i} className="card card-hover" style={{ display:"flex", alignItems:"center", gap:"14px", padding:"10px 16px" }}>
              {/* Thumbnail */}
              <div style={{ width:"56px", height:"56px", borderRadius:"10px", overflow:"hidden", flexShrink:0, background:"var(--bg2)", border:"1px solid var(--border)" }}>
                {thumbUrl
                  ? <img
                      src={thumbUrl}
                      alt="analyzed"
                      style={{ width:"100%", height:"100%", objectFit:"cover", display:"block" }}
                    />
                  : <div style={{ width:"100%", height:"100%", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"22px", background:EMOTION_BG[emotion]||"rgba(99,102,241,0.12)" }}>
                      {EMOTION_EMOJI[emotion]||"😐"}
                    </div>
                }
              </div>
              {/* Badges */}
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ display:"flex", gap:"6px", flexWrap:"wrap" }}>
                  <span className="badge badge-info">🎂 {avgAge}</span>
                  <span className={`badge ${smilePct>50?"badge-success":"badge-info"}`}>😊 {smilePct}%</span>
                  <span className="badge" style={{ background:EMOTION_BG[emotion], color:EMOTION_COLOR[emotion]||"var(--text)" }}>{EMOTION_EMOJI[emotion]} {item.dominant_emotion||"—"}</span>
                  {item.num_faces>1 && <span className="badge badge-cyan">👥 {item.num_faces}</span>}
                </div>
              </div>
              {/* Actions */}
              <div style={{ display:"flex", alignItems:"center", gap:"8px", flexShrink:0 }}>
                <p style={{ color:"var(--text3)", fontSize:"11px" }}>{item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}</p>
                {item.id && <button className="btn btn-secondary btn-icon" onClick={()=>downloadReport(item.id)} title="Download PDF">📄</button>}
                {item.id && <button className="btn btn-danger btn-icon" onClick={()=>deleteItem(item.id)} disabled={deleting===item.id} title="Delete">🗑️</button>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── ANALYTICS TAB ─────────────────────────────────────────────────
function AnalyticsTab() {
  const [data, setData]     = useState(null);
  const [trends, setTrends] = useState([]);
  const [ageDist, setAgeDist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [trendDays, setTrendDays] = useState(7);

  const load = async (days=7) => {
    setLoading(true);
    try {
      const [sumRes, trendRes, ageRes] = await Promise.all([
        axios.get(`${API}/api/analytics/summary`, { headers:authHdr() }),
        axios.get(`${API}/api/analytics/trends?days=${days}`, { headers:authHdr() }).catch(()=>({data:[]})),
        axios.get(`${API}/api/analytics/age-distribution`, { headers:authHdr() }).catch(()=>({data:{age_ranges:[]}})),
      ]);
      setData(sumRes.data);
      setTrends(trendRes.data||[]);
      setAgeDist(ageRes.data?.age_ranges||[]);
    } catch { toast.error("Failed to load analytics"); }
    setLoading(false);
  };

  useEffect(() => { load(trendDays); }, [trendDays]);

  if (loading) return <LoadingState text="Loading analytics..." />;

  const emotionData = (data?.emotion_distribution||[]).map(e=>({ name:e.emotion, value:e.count, color:EMOTION_COLOR[e.emotion.toLowerCase()]||"#6366f1" }));
  const topEmotion  = emotionData.length ? emotionData.reduce((a,b)=>a.value>b.value?a:b).name : "—";

  const stats = [
    { label:"Total Analyses", value:data?.total_predictions??"—", icon:"🔍", color:"#6366f1", sub:"all time" },
    { label:"Avg Smile",      value:data?.smile_percentage!=null?`${Math.round(data.smile_percentage)}%`:"—", icon:"😊", color:"#10b981", sub:"across all faces" },
    { label:"Avg Age",        value:data?.avg_age!=null?Math.round(data.avg_age):"—", icon:"🎂", color:"#f59e0b", sub:"predicted" },
    { label:"Top Emotion",    value:topEmotion, icon:"🎭", color:"#06b6d4", sub:"most common" },
  ];

  return (
    <div className="fade-in">
      <PageHeader title={<>Analytics <span className="gradient-text">Dashboard</span></>} subtitle="Insights from your face analyses" />

      {/* Stat cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"14px", marginBottom:"24px" }}>
        {stats.map(s=>(
          <div key={s.label} className="stat-card">
            <div style={{ fontSize:"26px" }}>{s.icon}</div>
            <p style={{ fontSize:"28px", fontWeight:"900", color:s.color, lineHeight:1 }}>{s.value}</p>
            <p style={{ fontWeight:"600", fontSize:"12px" }}>{s.label}</p>
            <p style={{ color:"var(--text3)", fontSize:"11px" }}>{s.sub}</p>
          </div>
        ))}
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"20px", marginBottom:"20px" }}>
        {/* Emotion bar */}
        {emotionData.length>0 && (
          <div className="card">
            <h3 style={{ fontWeight:"700", marginBottom:"16px", fontSize:"14px" }}>Emotion Breakdown</h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={emotionData} barSize={28}>
                <XAxis dataKey="name" tick={{ fill:"var(--text2)", fontSize:11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill:"var(--text3)", fontSize:10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background:"var(--card2)", border:"1px solid var(--border)", borderRadius:"10px", color:"var(--text)" }} cursor={{ fill:"rgba(99,102,241,0.06)" }} />
                <Bar dataKey="value" radius={[6,6,0,0]}>{emotionData.map((e,i)=><Cell key={i} fill={e.color} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Emotion pie */}
        {emotionData.length>0 && (
          <div className="card">
            <h3 style={{ fontWeight:"700", marginBottom:"16px", fontSize:"14px" }}>Emotion Distribution</h3>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={emotionData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={75} label={({name,percent})=>`${name} ${(percent*100).toFixed(0)}%`} labelLine={false}>
                  {emotionData.map((e,i)=><Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip contentStyle={{ background:"var(--card2)", border:"1px solid var(--border)", borderRadius:"10px", color:"var(--text)" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Trend chart */}
      {trends.length>0 && (
        <div className="card" style={{ marginBottom:"20px" }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:"16px" }}>
            <h3 style={{ fontWeight:"700", fontSize:"14px" }}>Prediction Trend</h3>
            <div style={{ display:"flex", gap:"6px" }}>
              {[7,14,30].map(d=>(
                <button key={d} onClick={()=>setTrendDays(d)} className={`btn ${trendDays===d?"btn-primary":"btn-secondary"}`} style={{ padding:"5px 12px", fontSize:"12px" }}>{d}d</button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={trends}>
              <defs>
                <linearGradient id="colorPred" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fill:"var(--text2)", fontSize:11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:"var(--text3)", fontSize:10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background:"var(--card2)", border:"1px solid var(--border)", borderRadius:"10px", color:"var(--text)" }} />
              <Legend />
              <Area type="monotone" dataKey="prediction_count" stroke="#6366f1" fill="url(#colorPred)" strokeWidth={2} name="Predictions" />
              <Line type="monotone" dataKey="avg_age" stroke="#f59e0b" strokeWidth={2} dot={false} name="Avg Age" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Age distribution */}
      {ageDist.length>0 && (
        <div className="card">
          <h3 style={{ fontWeight:"700", marginBottom:"16px", fontSize:"14px" }}>Age Range Distribution</h3>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={ageDist} barSize={32}>
              <XAxis dataKey="age_range" tick={{ fill:"var(--text2)", fontSize:11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:"var(--text3)", fontSize:10 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background:"var(--card2)", border:"1px solid var(--border)", borderRadius:"10px", color:"var(--text)" }} />
              <Bar dataKey="count" radius={[6,6,0,0]} fill="#06b6d4" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ── INSIGHTS TAB ──────────────────────────────────────────────────
function InsightsTab() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [streak, setStreak] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const [insRes, histRes] = await Promise.all([
          axios.get(`${API}/api/prediction/insights`, { headers:authHdr() }),
          axios.get(`${API}/api/prediction/history?limit=30`, { headers:authHdr() }),
        ]);
        setData(insRes.data);

        // Calculate streak (consecutive days with analyses)
        const preds = histRes.data.predictions || histRes.data || [];
        const days = new Set(preds.map(p => p.created_at ? new Date(p.created_at).toDateString() : null).filter(Boolean));
        let s = 0;
        const today = new Date();
        for (let i=0; i<30; i++) {
          const d = new Date(today); d.setDate(d.getDate()-i);
          if (days.has(d.toDateString())) s++; else break;
        }
        setStreak(s);
      } catch { toast.error("Failed to load insights"); }
      setLoading(false);
    })();
  }, []);

  if (loading) return <LoadingState text="Generating insights..." />;

  const insights = data?.insights || [];
  const totalFaces = data?.total_faces_analyzed || 0;

  return (
    <div className="fade-in">
      <PageHeader title={<>AI <span className="gradient-text">Insights</span></>} subtitle="Smart analysis of your face detection patterns" />

      {/* Streak card */}
      <div className="card" style={{ marginBottom:"24px", background:"linear-gradient(135deg,rgba(99,102,241,0.15),rgba(6,182,212,0.08))", border:"1px solid rgba(99,102,241,0.3)", display:"flex", alignItems:"center", gap:"20px", padding:"20px 24px" }}>
        <div style={{ fontSize:"48px" }}>🔥</div>
        <div>
          <p style={{ color:"var(--text3)", fontSize:"11px", fontWeight:"700", letterSpacing:"0.1em" }}>DAILY STREAK</p>
          <p style={{ fontSize:"40px", fontWeight:"900", lineHeight:1 }} className="gradient-text">{streak} day{streak!==1?"s":""}</p>
          <p style={{ color:"var(--text3)", fontSize:"13px", marginTop:"4px" }}>
            {streak===0 ? "Start your streak — analyze an image today!" : streak>=7 ? "🏆 Amazing consistency!" : streak>=3 ? "Keep it up!" : "Good start!"}
          </p>
        </div>
        <div style={{ marginLeft:"auto", textAlign:"center" }}>
          <p style={{ fontSize:"32px", fontWeight:"900", color:"#06b6d4" }}>{totalFaces}</p>
          <p style={{ color:"var(--text3)", fontSize:"12px" }}>Total Faces Analyzed</p>
        </div>
      </div>

      {/* Insight cards */}
      {insights.length===0 && (
        <div className="card" style={{ textAlign:"center", padding:"60px" }}>
          <div style={{ fontSize:"48px", marginBottom:"14px" }}>💡</div>
          <p style={{ color:"var(--text2)" }}>{data?.summary || "Analyze more images to unlock insights!"}</p>
        </div>
      )}

      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))", gap:"16px" }}>
        {insights.map((ins,i) => (
          <div key={i} className="card card-hover fade-in" style={{ padding:"20px", borderLeft:`3px solid ${ins.color}`, animationDelay:`${i*0.08}s` }}>
            <div style={{ display:"flex", alignItems:"center", gap:"12px", marginBottom:"10px" }}>
              <div style={{ width:"40px", height:"40px", background:`${ins.color}22`, borderRadius:"12px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"20px" }}>{ins.icon}</div>
              <p style={{ fontWeight:"700", fontSize:"14px", color:ins.color }}>{ins.title}</p>
            </div>
            <p style={{ color:"var(--text2)", fontSize:"13px", lineHeight:1.6 }}>{ins.text}</p>
          </div>
        ))}
      </div>

      {/* Achievement badges */}
      {totalFaces > 0 && (
        <div style={{ marginTop:"28px" }}>
          <h3 style={{ fontWeight:"700", marginBottom:"16px", fontSize:"15px" }}>🏅 Achievements</h3>
          <div style={{ display:"flex", gap:"12px", flexWrap:"wrap" }}>
            {[
              { icon:"🔍", label:"First Analysis",  unlocked:totalFaces>=1,  req:1 },
              { icon:"👥", label:"10 Faces",         unlocked:totalFaces>=10, req:10 },
              { icon:"💯", label:"100 Faces",        unlocked:totalFaces>=100,req:100 },
              { icon:"🔥", label:"3-Day Streak",     unlocked:streak>=3,      req:"3 days" },
              { icon:"🏆", label:"7-Day Streak",     unlocked:streak>=7,      req:"7 days" },
              { icon:"📊", label:"Power User",       unlocked:(data?.insights?.length||0)>=5, req:"5 insights" },
            ].map(a=>(
              <div key={a.label} style={{ display:"flex", alignItems:"center", gap:"10px", padding:"10px 16px", borderRadius:"12px", background: a.unlocked?"linear-gradient(135deg,rgba(99,102,241,0.2),rgba(6,182,212,0.1))":"var(--card)", border:`1px solid ${a.unlocked?"rgba(99,102,241,0.4)":"var(--border)"}`, opacity: a.unlocked?1:0.45 }}>
                <span style={{ fontSize:"22px" }}>{a.icon}</span>
                <div>
                  <p style={{ fontWeight:"700", fontSize:"12px" }}>{a.label}</p>
                  <p style={{ color:"var(--text3)", fontSize:"10px" }}>{a.unlocked?"✅ Unlocked":`Req: ${a.req}`}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── PROFILE TAB ───────────────────────────────────────────────────
function ProfileTab({ onLogout }) {
  const [profile, setProfile] = useState(null);
  const [stats, setStats]     = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm]       = useState({});
  const [saving, setSaving]   = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [pRes, sRes] = await Promise.all([
          axios.get(`${API}/api/users/profile`, { headers: authHdr() }),
          axios.get(`${API}/api/analytics/summary`, { headers: authHdr() }).catch(() => ({ data: null })),
        ]);
        setProfile(pRes.data);
        setForm({ first_name: pRes.data.first_name, last_name: pRes.data.last_name, phone: pRes.data.phone });
        setStats(sRes.data);
      } catch { toast.error("Failed to load profile"); }
    })();
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const res = await axios.put(`${API}/api/users/profile`, form, { headers: authHdr() });
      setProfile(res.data); setEditing(false); toast.success("Profile updated!");
    } catch { toast.error("Update failed"); }
    setSaving(false);
  };

  if (!profile) return <LoadingState text="Loading profile..." />;

  const initials = `${profile.first_name?.[0] || ""}${profile.last_name?.[0] || ""}`.toUpperCase();
  const topEmotion = stats?.emotion_distribution?.length
    ? stats.emotion_distribution.reduce((a, b) => a.count > b.count ? a : b).emotion : "—";

  return (
    <div className="fade-in" style={{ maxWidth: "600px" }}>
      <PageHeader title={<>My <span className="gradient-text">Profile</span></>} subtitle="Manage your account and view your stats" />

      {/* Avatar */}
      <div className="card" style={{ display: "flex", alignItems: "center", gap: "20px", marginBottom: "20px", padding: "24px", background: "linear-gradient(135deg,rgba(99,102,241,0.1),rgba(6,182,212,0.05))" }}>
        <div style={{ width: "72px", height: "72px", background: "linear-gradient(135deg,#6366f1,#06b6d4)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "26px", fontWeight: "900", color: "#fff", flexShrink: 0, boxShadow: "0 4px 20px rgba(99,102,241,0.5)" }}>
          {initials}
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: "22px", fontWeight: "800" }}>{profile.first_name} {profile.last_name}</p>
          <p style={{ color: "var(--text3)", fontSize: "13px" }}>{profile.email}</p>
          <span className={`badge ${profile.role === "admin" ? "badge-warning" : "badge-info"}`} style={{ marginTop: "6px" }}>
            {profile.role === "admin" ? "👑 Admin" : "👤 User"}
          </span>
        </div>
        <button className="btn btn-secondary" onClick={() => setEditing(v => !v)}>{editing ? "✕ Cancel" : "✏️ Edit"}</button>
      </div>

      {/* Edit form */}
      {editing && (
        <div className="card fade-in" style={{ marginBottom: "20px", padding: "20px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
            <div>
              <label style={{ fontSize: "12px", color: "var(--text3)", fontWeight: "600" }}>First Name</label>
              <input value={form.first_name || ""} onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))} style={{ marginTop: "4px" }} />
            </div>
            <div>
              <label style={{ fontSize: "12px", color: "var(--text3)", fontWeight: "600" }}>Last Name</label>
              <input value={form.last_name || ""} onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))} style={{ marginTop: "4px" }} />
            </div>
          </div>
          <div style={{ marginBottom: "14px" }}>
            <label style={{ fontSize: "12px", color: "var(--text3)", fontWeight: "600" }}>Phone</label>
            <input value={form.phone || ""} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} style={{ marginTop: "4px" }} />
          </div>
          <button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? "Saving..." : "💾 Save Changes"}</button>
        </div>
      )}

      {/* Info rows */}
      <div className="card" style={{ marginBottom: "20px", padding: "20px" }}>
        {[
          { icon: "📧", label: "Email",  value: profile.email },
          { icon: "📱", label: "Phone",  value: profile.phone },
          { icon: "📅", label: "Joined", value: profile.created_at ? new Date(profile.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "—" },
        ].map(row => (
          <div key={row.label} style={{ display: "flex", alignItems: "center", gap: "14px", padding: "12px 0", borderBottom: "1px solid var(--border2)" }}>
            <span style={{ fontSize: "18px", width: "28px", textAlign: "center" }}>{row.icon}</span>
            <div>
              <p style={{ color: "var(--text3)", fontSize: "10px", fontWeight: "700", letterSpacing: "0.08em" }}>{row.label.toUpperCase()}</p>
              <p style={{ fontWeight: "500", fontSize: "14px" }}>{row.value || "—"}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Quick stats */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px", marginBottom: "20px" }}>
          {[
            { label: "Analyses",    value: stats.total_predictions ?? "—", icon: "🔍" },
            { label: "Avg Smile",   value: stats.smile_percentage != null ? `${Math.round(stats.smile_percentage)}%` : "—", icon: "😊" },
            { label: "Top Emotion", value: topEmotion, icon: "🎭" },
          ].map(s => (
            <div key={s.label} className="card" style={{ textAlign: "center", padding: "16px" }}>
              <div style={{ fontSize: "22px", marginBottom: "6px" }}>{s.icon}</div>
              <p style={{ fontWeight: "800", fontSize: "20px" }} className="gradient-text">{s.value}</p>
              <p style={{ color: "var(--text3)", fontSize: "11px", marginTop: "2px" }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <button className="btn btn-danger" onClick={onLogout} style={{ width: "100%", justifyContent: "center" }}>🚪 Sign Out</button>
    </div>
  );
}

