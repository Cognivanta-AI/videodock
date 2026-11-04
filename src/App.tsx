import { useMemo, useState } from 'react';
import { Activity, CheckCircle2, Clapperboard, Clock3, Film, FolderOpen, Play, Search, X } from 'lucide-react';

type Status = 'Em revisão' | 'Renderizando' | 'Aprovado';
type Video = { id: string; title: string; channel: string; status: Status; duration: string; updated: string; thumbnail?: string; playbackUrl?: string };

// Demonstration content only. Replace with a protected API response once deployed.
const demoVideos: Video[] = [
  { id: 'demo-1', title: 'How Humans Survived Before Fire', channel: 'Curious Ancestors', status: 'Em revisão', duration: '10:24', updated: '04 nov 2026' },
  { id: 'demo-2', title: 'The First Human Settlements', channel: 'Curious Ancestors', status: 'Renderizando', duration: '—', updated: '04 nov 2026' },
  { id: 'demo-3', title: 'Why Ancient Civilizations Collapsed', channel: 'History Vault', status: 'Aprovado', duration: '08:46', updated: '03 nov 2026' },
];

function statusClass(status: Status) { return status === 'Aprovado' ? 'approved' : status === 'Renderizando' ? 'rendering' : 'review'; }

export default function App() {
  const [channel, setChannel] = useState('all');
  const [search, setSearch] = useState('');
  const [activeVideo, setActiveVideo] = useState<Video | null>(null);
  const channels = useMemo(() => Array.from(new Set(demoVideos.map(v => v.channel))), []);
  const filtered = demoVideos.filter(v => (channel === 'all' || v.channel === channel) && (v.title + ' ' + v.channel).toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const stats = [
    { label: 'Vídeos', value: filtered.length, icon: Film },
    { label: 'Em revisão', value: filtered.filter(v => v.status === 'Em revisão').length, icon: Clock3 },
    { label: 'Aprovados', value: filtered.filter(v => v.status === 'Aprovado').length, icon: CheckCircle2 },
  ];
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Clapperboard size={23}/></div><div><strong>VideoDock</strong><small>Video Production Studio</small></div></div>
      <div className="nav-heading">WORKSPACE</div>
      <div className="nav-item active"><Film size={17}/> Biblioteca <span className="nav-count">{demoVideos.length}</span></div>
      <div className="nav-item"><Activity size={17}/> Produção</div>
      <div className="nav-heading">CANAIS</div>
      <button className={`channel-nav ${channel === 'all' ? 'selected' : ''}`} onClick={() => setChannel('all')}><FolderOpen size={16}/> Todos os canais</button>
      {channels.map(c => <button key={c} className={`channel-nav ${channel === c ? 'selected' : ''}`} onClick={() => setChannel(c)}><span className="channel-dot"/>{c}</button>)}
      <div className="sidebar-footer">VideoDock <span>v0.1 · Demo</span></div>
    </aside>
    <main className="content"><div className="topline"><div><div className="eyebrow">CONTENT OPERATIONS</div><h1>Biblioteca de vídeos</h1><p>Visualize, acompanhe e revise as produções dos seus canais.</p></div><span className="demo-pill">Ambiente de demonstração</span></div>
      <div className="controls"><label className="search"><Search size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar vídeos ou canais" aria-label="Buscar vídeos ou canais"/></label><select aria-label="Filtrar por canal" value={channel} onChange={e => setChannel(e.target.value)}><option value="all">Todos os canais</option>{channels.map(c => <option key={c} value={c}>{c}</option>)}</select></div>
      <div className="stats">{stats.map(s => <section className="stat" key={s.label}><div className="stat-label"><span>{s.label}</span><s.icon size={18}/></div><strong>{s.value}</strong></section>)}</div>
      <section className="panel"><div className="panel-head"><div><h2>Produções recentes</h2><p>Organizadas por canal e status de produção</p></div><span className="item-count">{filtered.length} vídeo(s)</span></div>
      {filtered.length ? <div className="video-list">{filtered.map(v => <button key={v.id} className="video-row" onClick={() => setActiveVideo(v)}><div className="thumbnail">{v.thumbnail ? <img src={v.thumbnail} alt=""/> : <Play size={24} fill="currentColor"/>}</div><div className="video-info"><strong>{v.title}</strong><small>{v.channel} <span className="separator">·</span> {v.duration} <span className="separator">·</span> {v.updated}</small></div><span className={`status ${statusClass(v.status)}`}><span className="status-dot"/>{v.status}</span><span className="view-label">Visualizar →</span></button>)}</div> : <div className="empty">Nenhum vídeo corresponde aos filtros selecionados.</div>}</section>
      <footer>VideoDock · Multichannel media review <span>Os vídeos desta página são demonstrativos.</span></footer>
    </main>
    {activeVideo && <div className="modal-backdrop" role="presentation" onMouseDown={() => setActiveVideo(null)}><div className="modal" role="dialog" aria-modal="true" aria-label={activeVideo.title} onMouseDown={e => e.stopPropagation()}><button className="close" aria-label="Fechar" onClick={() => setActiveVideo(null)}><X size={20}/></button><h2>{activeVideo.title}</h2><p>{activeVideo.channel} · {activeVideo.duration} · {activeVideo.status}</p>{activeVideo.playbackUrl ? <video controls playsInline src={activeVideo.playbackUrl} className="player"/> : <div className="no-player"><Play size={32}/><strong>Prévia ainda não disponível</strong><span>Este é um item de demonstração. O player usará a URL segura do vídeo após integrar o backend.</span></div>}</div></div>}
  </div>;
}
