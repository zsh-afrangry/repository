import type { LocationQuery } from 'vue-router';
// Navigation-only memory: content is always read from the API, never this cache.
export const workspacePositions = new Map<string, {
    y: number;
    focus: string;
    query: LocationQuery;
}>();
