export type Status = 'review' | 'rendering' | 'approved' | 'rejected' | 'published' | 'failed';
export type Channel = { id: string; name: string };
export type Video = {
  id: string; channel_id: string; title: string; description: string; status: Status;
  duration_seconds: number; resolution: string; fps: number; video_path: string;
  thumbnail_path: string; generator: string; style: string; created_at: string;
};
export type Catalog = { channels: Channel[]; videos: Video[] };
export const statusLabels: Record<Status, string> = { review: 'Em revisão', rendering: 'Renderizando', approved: 'Aprovado', rejected: 'Rejeitado', published: 'Publicado', failed: 'Falhou' };
const statuses = new Set(Object.keys(statusLabels));
const slug = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Catálogo inválido: objeto esperado.');
  return value as Record<string, unknown>;
}
function string(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error('Catálogo inválido: texto obrigatório.');
  return value;
}
function safePath(value: unknown): string {
  const path = string(value);
  if (!/^[a-zA-Z0-9_./-]+$/.test(path) || path.startsWith('/') || path.split('/').some(part => !part || part === '.' || part === '..')) throw new Error('Caminho de mídia inválido.');
  return path;
}
export function publicAssetUrl(base: string, path: string): string { return `${base.endsWith('/') ? base : base + '/'}${safePath(path)}`; }
export function formatDuration(seconds: number): string {
  const total = Math.round(seconds);
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}
export function parseCatalog(value: unknown): Catalog {
  const data = record(value);
  if (!Array.isArray(data.channels) || !Array.isArray(data.videos)) throw new Error('Catálogo inválido: canais e vídeos obrigatórios.');
  const ids = new Set<string>();
  const channels = data.channels.map(raw => {
    const c = record(raw), id = string(c.id), name = string(c.name);
    if (!slug.test(id) || ids.has(id)) throw new Error('Canal inválido ou duplicado.');
    ids.add(id); return { id, name };
  });
  const videoIds = new Set<string>();
  const videos = data.videos.map(raw => {
    const v = record(raw), id = string(v.id), channel_id = string(v.channel_id);
    if (!slug.test(id) || videoIds.has(id) || !ids.has(channel_id)) throw new Error('Vídeo duplicado ou canal desconhecido.');
    videoIds.add(id);
    const status = string(v.status) as Status;
    if (!statuses.has(status)) throw new Error('Status inválido.');
    const duration_seconds = v.duration_seconds, fps = v.fps, resolution = string(v.resolution);
    if (typeof duration_seconds !== 'number' || !Number.isFinite(duration_seconds) || duration_seconds <= 0 || duration_seconds > 86400 || typeof fps !== 'number' || !Number.isFinite(fps) || fps <= 0 || fps > 240 || !/^[1-9]\d*x[1-9]\d*$/.test(resolution)) throw new Error('Metadados de vídeo inválidos.');
    const created_at = string(v.created_at);
    const day = created_at.slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2}))?$/.test(created_at) || Number.isNaN(Date.parse(created_at)) || Number.isNaN(Date.parse(day)) || new Date(day).toISOString().slice(0, 10) !== day) throw new Error('Data inválida.');
    const video_path = safePath(v.video_path), thumbnail_path = safePath(v.thumbnail_path), prefix = `videos/${channel_id}/`;
    if (!video_path.startsWith(prefix) || !video_path.endsWith('.mp4') || !thumbnail_path.startsWith(prefix) || !/\.jpe?g$/.test(thumbnail_path)) throw new Error('Mídia fora do canal ou formato inválido.');
    for (const field of ['description', 'generator', 'style']) if (typeof v[field] !== 'string') throw new Error('Metadados textuais inválidos.');
    return { id, channel_id, title: string(v.title), description: v.description as string, status, duration_seconds, resolution, fps, video_path, thumbnail_path, generator: v.generator as string, style: v.style as string, created_at };
  });
  return { channels, videos };
}
