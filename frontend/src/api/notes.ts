import { apiFetch } from './client';
import type { NoteTopic, TopicData, TopicSummary } from '../features/notes/types';
export const listNoteTopics = (signal?: AbortSignal) => apiFetch<TopicSummary[]>('/notes/topics', { signal });
export const getNoteTopic = (id: string, signal?: AbortSignal) => apiFetch<NoteTopic>(`/notes/topics/${encodeURIComponent(id)}`, { signal });
export const createNoteTopic = (data: TopicData) => apiFetch<NoteTopic>('/notes/topics', { method: 'POST', body: JSON.stringify(data) });
export const saveNoteTopic = ({ id, ...data }: NoteTopic) => apiFetch<NoteTopic>(`/notes/topics/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteNoteTopic = (topic: NoteTopic) => apiFetch<void>(`/notes/topics/${encodeURIComponent(topic.id)}?version=${topic.version}`, { method: 'DELETE' });
