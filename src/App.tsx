import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, CheckCircle2, Clapperboard, Clock3, Film, FolderOpen, Play, Search, X } from 'lucide-react';
import { formatDuration, parseCatalog, publicAssetUrl, statusLabels } from './catalog';
import type { Catalog, Status } from './catalog';

const base = import.meta.env.BASE_URL;
function statusClass(status: Status) { return status === 'approved' || status === 'published' ? 'approved' : status === 'rendering' ? 'rendering' : status === 'failed' || status === 'rejected' ? 'failed' : 'review'; }
const selectedId = () => new URLSearchParams(window.location.hash.slice(1)).get('video');
const dateLabel = (date: string) => new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(date));

export default function App() {
  const [catalog, setCatalog] = useState<Catalog>({ channels: [], videos: [] });
  const [loading, setLoading] = useState(true);
  const [catalogError, setCatalogError] = useState('');
  const [retry, setRetry] = useState(0);
  const [channel, setChannel] = useState('all');
  const [search, setSearch] = useState('');
  const [activeId, setActiveId] = useState<string | null>(selectedId);
  const [playerError, setPlayerError] = useState('');
  const dialog = useRef<HTMLDivElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const { channels, videos } = catalog;
  const names = useMemo(() => new Map(channels.map(c => [c.id, c.name])), [channels]);
  const activeVideo = videos.find(v => v.id === activeId);
  const filtered = videos.filter(v => (channel === 'all' || v.channel_id === channel) && (v.title + ' ' + names.get(v.channel_id)).toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const closeVideo = useCallback(() => {
    setActiveId(null);
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setCatalogError('');
    fetch(publicAssetUrl(base, 'data/videos.json'), { signal: controller.signal, cache: 'no-cache' })
      .then(response => { if (!response.ok) throw new Error('Catálogo indisponível.'); return response.json(); })
      .then(data => { setCatalog(parseCatalog(data)); setLoading(false); })
      .catch(error => { if (error.name !== 'AbortError') { setCatalogError('Não foi possível carregar o catálogo de vídeos. Tente novamente.'); setLoading(false); } });
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    const update = () => setActiveId(selectedId());
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  useEffect(() => {
    setPlayerError('');
    if (!activeVideo) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden'; closeButton.current?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); closeVideo(); }
      if (event.key === 'Tab') {
        const nodes = dialog.current?.querySelectorAll<HTMLElement>('button, a[href], video, [tabindex="0"]');
        if (!nodes?.length) return;
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', keydown);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', keydown); previous?.focus(); };
  }, [activeVideo, closeVideo]);
  function openVideo(id: string) { setActiveId(id); window.location.hash = `video=${encodeURIComponent(id)}`; }
  const stats = [
    { label: 'Vídeos', value: filtered.length, icon: Film },
    { label: 'Em revisão', value: filtered.filter(v => v.status === 'review').length, icon: Clock3 },
    { label: 'Aprovados', value: filtered.filter(v => v.status === 'approved').length, icon: CheckCircle2 },
  ];
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Clapperboard size={23}/></div><div><strong>VideoDock</strong><small>Video Production Studio</small></div></div>
      <div className="nav-heading">WORKSPACE</div>
      <div className="nav-item active"><Film size={17}/> Biblioteca <span className="nav-count">{videos.length}</span></div>
      <div className="nav-item"><Activity size={17}/> Produção</div>
      <div className="nav-heading">CANAIS</div>
      <button className={`channel-nav ${channel === 'all' ? 'selected' : ''}`} onClick={() => setChannel('all')}><FolderOpen size={16}/> Todos os canais</button>
      {channels.map(c => <button key={c.id} className={`channel-nav ${channel === c.id ? 'selected' : ''}`} onClick={() => setChannel(c.id)}><span className="channel-dot"/>{c.name}</button>)}
      <div className="sidebar-footer">VideoDock <span>v0.2 · Catálogo</span></div>
    </aside>
    <main className="content"><div className="topline"><div><div className="eyebrow">CONTENT OPERATIONS</div><h1>Biblioteca de vídeos</h1><p>Visualize, acompanhe e revise as produções dos seus canais.</p></div><span className="demo-pill">Catálogo de produções</span></div>
      <div className="controls"><label className="search"><Search size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar vídeos ou canais" aria-label="Buscar vídeos ou canais"/></label><select aria-label="Filtrar por canal" value={channel} onChange={e => setChannel(e.target.value)}><option value="all">Todos os canais</option>{channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
      <div className="stats">{stats.map(s => <section className="stat" key={s.label}><div className="stat-label"><span>{s.label}</span><s.icon size={18}/></div><strong>{s.value}</strong></section>)}</div>
      <section className="panel" aria-busy={loading}><div className="panel-head"><div><h2>Produções recentes</h2><p>Organizadas por canal e status de produção</p></div><span className="item-count">{filtered.length} vídeo(s)</span></div>
      {loading ? <div className="empty" role="status">Carregando catálogo…</div> : catalogError ? <div className="empty" role="alert">{catalogError} <button className="retry" onClick={() => setRetry(n => n + 1)}>Tentar novamente</button></div> : filtered.length ? <div className="video-list">{filtered.map(v => <button key={v.id} className="video-row" onClick={() => openVideo(v.id)}><div className="thumbnail"><img src={publicAssetUrl(base, v.thumbnail_path)} alt={`Miniatura de ${v.title}`} loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }}/><Play size={24} className="thumbnail-fallback"/></div><div className="video-info"><strong>{v.title}</strong><small>{names.get(v.channel_id)} <span className="separator">·</span> {formatDuration(v.duration_seconds)} <span className="separator">·</span> {dateLabel(v.created_at)}</small></div><span className={`status ${statusClass(v.status)}`}><span className="status-dot"/>{statusLabels[v.status]}</span><span className="view-label">Visualizar →</span></button>)}</div> : <div className="empty">Nenhum vídeo corresponde aos filtros selecionados.</div>}</section>
      {!loading && !catalogError && activeId && !activeVideo && <p role="alert">O vídeo deste link não foi encontrado no catálogo.</p>}
      <footer>VideoDock · Multichannel media review <span>Arquivos públicos · aprovação editorial permanece humana.</span></footer>
    </main>
    {activeVideo && <div className="modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) closeVideo(); }}><div ref={dialog} className="modal" role="dialog" aria-modal="true" aria-label={activeVideo.title}><button ref={closeButton} className="close" aria-label="Fechar" onClick={closeVideo}><X size={20}/></button><h2>{activeVideo.title}</h2><p>{names.get(activeVideo.channel_id)} · {formatDuration(activeVideo.duration_seconds)} · {statusLabels[activeVideo.status]}</p><video key={activeVideo.id} controls playsInline preload="metadata" tabIndex={0} poster={publicAssetUrl(base, activeVideo.thumbnail_path)} src={publicAssetUrl(base, activeVideo.video_path)} className="player" onError={() => setPlayerError('Não foi possível reproduzir este vídeo. Verifique a conexão ou abra o arquivo MP4 diretamente.')}/>{playerError && <p className="player-error" role="alert">{playerError}</p>}<p>{activeVideo.description}</p><div className="player-details"><span>{activeVideo.resolution} · {activeVideo.fps} fps · {activeVideo.style}</span><a href={publicAssetUrl(base, activeVideo.video_path)}>Abrir MP4</a></div></div></div>}
  </div>;
}
