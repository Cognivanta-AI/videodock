import test from 'node:test';
import assert from 'node:assert/strict';
import { parseCatalog, publicAssetUrl, formatDuration } from '../src/catalog.ts';
const catalog=()=>({channels:[{id:'curious-ancestors',name:'Curious Ancestors'}],videos:[{id:'curious-ancestors-the-noise-outside',channel_id:'curious-ancestors',title:'The Noise Outside',description:'A prehistoric suspense micro-story.',status:'review',duration_seconds:30,resolution:'1280x720',fps:30,video_path:'videos/curious-ancestors/the-noise-outside/preview.mp4',thumbnail_path:'videos/curious-ancestors/the-noise-outside/thumbnail.jpg',generator:'FLUX.1 Schnell',style:'A3 Prehistoric Cave',created_at:'2026-11-04'}]});
test('real catalog preserves review status and base-relative assets',()=>{
 const c=parseCatalog(catalog());assert.equal(c.videos[0].status,'review');assert.equal(c.channels.length,1);
 assert.equal(publicAssetUrl('/videodock/',c.videos[0].video_path),'/videodock/videos/curious-ancestors/the-noise-outside/preview.mp4');
 assert.equal(formatDuration(30),'00:30');assert.equal(formatDuration(600),'10:00');
});
test('empty catalog is valid; malformed, duplicate and orphan records are rejected',()=>{
 assert.deepEqual(parseCatalog({channels:[],videos:[]}),{channels:[],videos:[]});
 for(const change of [c=>c.videos.push({...c.videos[0]}),c=>c.channels.push({...c.channels[0]}),c=>c.videos[0].channel_id='unknown',c=>c.videos[0].duration_seconds=NaN,c=>c.videos[0].fps=0,c=>c.videos[0].created_at='2026-02-31',c=>c.videos[0].status='automatically-approved']){
  const c=catalog();change(c);assert.throws(()=>parseCatalog(c));
 }
});
test('publisher defaults with blank optional metadata and ISO timestamps remain readable',()=>{
 const c=catalog();c.videos[0].description='';c.videos[0].generator='';c.videos[0].style='';c.videos[0].created_at='2026-11-04T06:10:30.123456Z';
 const parsed=parseCatalog(c);assert.equal(parsed.videos[0].description,'');assert.equal(parsed.videos[0].created_at,c.videos[0].created_at);
});
test('catalog never accepts external, encoded or traversal media paths',()=>{
 for(const path of ['https://evil.example/x.mp4','/videos/x.mp4','videos/../x.mp4','videos/curious-ancestors/%2e%2e/x.mp4','videos/other-channel/x.mp4','videos/curious-ancestors//x.mp4']){
  const c=catalog();c.videos[0].video_path=path;assert.throws(()=>parseCatalog(c));
 }
 assert.throws(()=>publicAssetUrl('/videodock/','../secret'));
});
