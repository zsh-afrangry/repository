import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router';
import { workspacePositions as positions } from './navigation';
import { renderNoteMarkdown, importNoteMarkdown } from '../utils/markdown';
import { listNoteTopics, getNoteTopic, createNoteTopic, saveNoteTopic, deleteNoteTopic } from '../../../api/notes';
import type { NoteTopic, TopicData, TopicSummary, KnowledgeUnit } from '../types';
/** API-backed workspace state; drafts stay separate until an atomic save succeeds. */
export function useNotesWorkspace() {
    const route = useRoute(), router = useRouter();
    const topics = ref<TopicSummary[]>([]), topic = ref<NoteTopic | null>(null);
    const loading = ref(false), saving = ref(false), error = ref(''), notice = ref('');
    const topicId = computed(() => String(route.params.topicId || '')), unitId = computed(() => String(route.params.unitId || ''));
    const unit = computed(() => topic.value?.units.find(u => u.id === unitId.value));
    const sections = computed(() => [...(topic.value?.sections || [])].sort((a, b) => a.order - b.order || a.id.localeCompare(b.id)));
    const queryText = computed(() => String(route.query.q || '')), sectionFilter = computed(() => String(route.query.section || ''));
    const view = computed(() => route.query.view === 'graph' ? 'graph' : 'directory');
    const selectedId = computed(() => String(route.query.selected || ''));
    const selected = computed(() => topic.value?.units.find(u => u.id === selectedId.value));
    const visibleUnits = computed(() => topic.value?.units.filter(u => (!sectionFilter.value || u.sectionId === sectionFilter.value) && `${u.title} ${u.tags.join(' ')} ${u.content}`.toLowerCase().includes(queryText.value.toLowerCase())) || []);
    const visibleTopics = computed(() => topics.value.filter(t => `${t.title} ${t.description}`.toLowerCase().includes(queryText.value.toLowerCase())));
    const form = ref<'' | 'topic' | 'section' | 'unit'>(''), editing = ref(false), editId = ref('');
    const draft = ref({ title: '', description: '', sortOrder: 0, preferredColumns: 3 });
    const draftUnit = ref<KnowledgeUnit>({ id: '', title: '', sectionId: '', content: '', tags: [] });
    const tagText = ref(''), previous = ref<string[]>([]), following = ref<string[]>([]), baseline = ref('');
    const formState = () => JSON.stringify(form.value === 'unit' || editing.value ? { unit: draftUnit.value, tags: tagText.value, previous: previous.value, following: following.value } : draft.value);
    const dirty = computed(() => Boolean(form.value || editing.value) && formState() !== baseline.value);
    const modalOpen = computed(() => Boolean(form.value || unitId.value));
    const modalLabel = computed(() => form.value === 'topic' ? '主题设置' : form.value === 'section' ? '目录设置' : editing.value || form.value === 'unit' ? '编辑知识单元' : '知识单元阅读器');
    const peerUnits = computed(() => topic.value?.units.filter(u => u.id !== draftUnit.value.id) || []);
    const markdown = computed(() => renderNoteMarkdown(unit.value?.content || ''));
    const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x));
    const newId = () => crypto.randomUUID();
    let request = 0, controller: AbortController | null = null;
    const workspacePath = () => `/notes/${topicId.value}`;
    const unitPath = (id: string) => `/notes/${topicId.value}/units/${id}`;
    const queryWith = (key: string, value: string) => ({ ...route.query, [key]: value || undefined });
    function changeQuery(key: string, value: string) { void router.replace({ path: route.path, query: queryWith(key, value) }); }
    function acceptDiscard() { return !dirty.value || window.confirm('存在未保存修改，确定放弃吗？'); }
    function resetForm() { form.value = ''; editing.value = false; editId.value = ''; baseline.value = ''; error.value = ''; }
    async function refreshIndex() { topics.value = await listNoteTopics(); }
    async function load() {
        const ticket = ++request;
        controller?.abort();
        controller = new AbortController();
        loading.value = true;
        error.value = '';
        const id = topicId.value;
        try {
            const [index, doc] = await Promise.all([listNoteTopics(controller.signal), id ? getNoteTopic(id, controller.signal) : Promise.resolve(null)]);
            if (ticket !== request)
                return;
            topics.value = index;
            topic.value = doc;
            document.title = doc ? `${doc.title} · 学习笔记` : '学习总览 · KnowledgeMap';
        }
        catch (e) {
            if (ticket === request && !(e instanceof DOMException && e.name === 'AbortError')) {
                topic.value = null;
                error.value = e instanceof Error ? e.message : '读取失败';
            }
        }
        finally {
            if (ticket === request)
                loading.value = false;
        }
    }
    async function reload() { if (!acceptDiscard())
        return; resetForm(); await load(); }
    watch(topicId, () => { resetForm(); notice.value = ''; void load(); }, { immediate: true });
    watch(unitId, () => { editing.value = false; form.value = ''; error.value = ''; notice.value = ''; });
    watch(modalOpen, async (open) => { if (!open) {
        await nextTick();
        const state = positions.get(topicId.value);
        if (state) {
            window.scrollTo({ top: state.y, behavior: 'instant' });
            document.querySelector<HTMLElement>(`[data-unit-id="${state.focus}"]`)?.focus({ preventScroll: true });
        }
    } });
    function guard() { if (saving.value)
        return false; if (!acceptDiscard())
        return false; resetForm(); return true; }
    onBeforeRouteLeave(guard);
    onBeforeRouteUpdate((to, from) => to.path !== from.path ? guard() : true);
    function beforeUnload(e: BeforeUnloadEvent) { if (dirty.value || saving.value) {
        e.preventDefault();
        e.returnValue = '';
    } }
    onMounted(() => window.addEventListener('beforeunload', beforeUnload));
    onBeforeUnmount(() => { controller?.abort(); window.removeEventListener('beforeunload', beforeUnload); document.title = 'KnowledgeMap'; });
    function rememberWorkspace(id: string) { positions.set(topicId.value, { y: window.scrollY, focus: id, query: clone(route.query) }); }
    function switchTopic(id: string) { if (!unitId.value && topicId.value)
        rememberWorkspace(selectedId.value); void router.push({ path: `/notes/${id}`, query: positions.get(id)?.query || {} }); }
    function openUnit(id: string) { rememberWorkspace(id); void router.push({ path: unitPath(id), query: route.query }); }
    function closeModal() { if (saving.value || !acceptDiscard())
        return; resetForm(); if (unitId.value)
        void router.push({ path: workspacePath(), query: route.query }); }
    function newTopic() { resetForm(); form.value = 'topic'; draft.value = { title: '', description: '', sortOrder: topics.value.length, preferredColumns: 3 }; baseline.value = formState(); }
    function editTopic() { if (!topic.value)
        return; resetForm(); form.value = 'topic'; editId.value = topic.value.id; draft.value = { title: topic.value.title, description: topic.value.description, sortOrder: topic.value.sortOrder, preferredColumns: topic.value.preferredColumns }; baseline.value = formState(); }
    function sectionForm(id = '') { resetForm(); form.value = 'section'; editId.value = id; const s = topic.value?.sections.find(s => s.id === id); draft.value = { title: s?.title || '', description: '', sortOrder: s?.order ?? sections.value.length, preferredColumns: 3 }; baseline.value = formState(); }
    function unitForm(existing?: KnowledgeUnit) { resetForm(); if (existing) {
        editing.value = true;
    }
    else
        form.value = 'unit'; draftUnit.value = existing ? clone(existing) : { id: newId(), title: '', sectionId: sections.value.find(s => s.id === sectionFilter.value)?.id || sections.value[0]?.id || '', content: '', tags: [] }; tagText.value = draftUnit.value.tags.join(', '); previous.value = (topic.value?.edges.filter(e => e.toUnitId === draftUnit.value.id).map(e => e.fromUnitId)) || []; following.value = (topic.value?.edges.filter(e => e.fromUnitId === draftUnit.value.id).map(e => e.toUnitId)) || []; baseline.value = formState(); }
    async function persist(data: NoteTopic) { const saved = await saveNoteTopic(data); topic.value = saved; notice.value = '已保存到数据库'; try {
        await refreshIndex();
    }
    catch {
        notice.value = '已保存到数据库；总览数量暂未刷新，请稍后重试';
    } return saved; }
    async function save() {
        if (saving.value)
            return;
        saving.value = true;
        error.value = '';
        try {
            if (form.value === 'topic') {
                if (!draft.value.title.trim())
                    throw new Error('请输入主题名称');
                if (editId.value && topic.value) {
                    await persist({ ...clone(topic.value), ...draft.value });
                    resetForm();
                }
                else {
                    const data: TopicData = { ...draft.value, example: false, sections: [], units: [], edges: [] };
                    const saved = await createNoteTopic(data);
                    resetForm();
                    saving.value = false;
                    await router.push(`/notes/${saved.id}`);
                }
            }
            else if (form.value === 'section' && topic.value) {
                const data = clone(topic.value), id = editId.value || newId();
                if (!draft.value.title.trim())
                    throw new Error('请输入目录名称');
                data.sections = data.sections.filter(s => s.id !== id).concat({ id, title: draft.value.title.trim(), order: draft.value.sortOrder });
                await persist(data);
                resetForm();
            }
            else if ((form.value === 'unit' || editing.value) && topic.value) {
                if (!draftUnit.value.title.trim() || !draftUnit.value.sectionId)
                    throw new Error('请填写标题并选择目录');
                const data = clone(topic.value), id = draftUnit.value.id;
                data.units = data.units.filter(u => u.id !== id).concat({ ...clone(draftUnit.value), title: draftUnit.value.title.trim(), tags: tagText.value.split(/[,，]/).map(t => t.trim()).filter(Boolean) });
                data.edges = data.edges.filter(e => e.fromUnitId !== id && e.toUnitId !== id).concat(previous.value.map(fromUnitId => ({ fromUnitId, toUnitId: id })), following.value.map(toUnitId => ({ fromUnitId: id, toUnitId })));
                await persist(data);
                resetForm();
                saving.value = false;
                if (unitId.value !== id)
                    await router.push({ path: unitPath(id), query: route.query });
            }
        }
        catch (e) {
            error.value = e instanceof Error ? e.message : '保存失败，草稿仍保留';
        }
        finally {
            saving.value = false;
        }
    }
    async function removeSection(id: string) { if (!topic.value || saving.value)
        return; if (topic.value.units.some(u => u.sectionId === id)) {
        error.value = '目录非空，请先编辑单元并迁移到其他目录';
        return;
    } const s = topic.value.sections.find(s => s.id === id); if (!confirm(`删除空目录「${s?.title}」？`))
        return; saving.value = true; try {
        const data = clone(topic.value);
        data.sections = data.sections.filter(s => s.id !== id);
        await persist(data);
        resetForm();
        if (sectionFilter.value === id)
            changeQuery('section', '');
    }
    catch (e) {
        error.value = String(e);
    }
    finally {
        saving.value = false;
    } }
    async function removeTopic() { if (!topic.value || saving.value)
        return; if (topic.value.sections.length || topic.value.units.length) {
        error.value = '主题非空，请先迁移或单独删除单元，再移除空目录';
        return;
    } if (!confirm(`删除空主题「${topic.value.title}」？`))
        return; saving.value = true; try {
        await deleteNoteTopic(topic.value);
        resetForm();
        saving.value = false;
        await router.push('/notes');
    }
    catch (e) {
        error.value = String(e);
    }
    finally {
        saving.value = false;
    } }
    async function removeUnit() { if (!topic.value || !unit.value || saving.value)
        return; const current = unit.value, count = topic.value.edges.filter(e => e.fromUnitId === current.id || e.toUnitId === current.id).length; if (!confirm(`删除「${current.title}」及其 ${count} 条关联依赖？其他知识单元将保留。`))
        return; saving.value = true; try {
        const data = clone(topic.value);
        data.units = data.units.filter(u => u.id !== current.id);
        data.edges = data.edges.filter(e => e.fromUnitId !== current.id && e.toUnitId !== current.id);
        await persist(data);
        saving.value = false;
        await router.push({ path: workspacePath(), query: { ...route.query, selected: undefined } });
    }
    catch (e) {
        error.value = String(e);
    }
    finally {
        saving.value = false;
    } }
    function dependencies(id: string, direction: 'before' | 'after') { if (!topic.value)
        return []; const ids = topic.value.edges.filter(e => direction === 'before' ? e.toUnitId === id : e.fromUnitId === id).map(e => direction === 'before' ? e.fromUnitId : e.toUnitId); return topic.value.units.filter(u => ids.includes(u.id)); }
    async function importFile(event: Event) { const input = event.target as HTMLInputElement, file = input.files?.[0]; input.value = ''; if (!file)
        return; try {
        if (file.size > 1000000)
            throw new Error('文件超过 1MB，请拆分后导入');
        const imported = importNoteMarkdown(await file.text(), file.name);
        unitForm();
        draftUnit.value = { ...draftUnit.value, ...imported };
        tagText.value = imported.tags.join(', ');
    }
    catch (e) {
        error.value = String(e);
    } }
    function exportDraft() { const content = JSON.stringify({ unit: draftUnit.value, tags: tagText.value, previous: previous.value, following: following.value }, null, 2); const url = URL.createObjectURL(new Blob([content], { type: 'application/json' })); const a = document.createElement('a'); a.href = url; a.download = 'notes-draft.json'; a.click(); URL.revokeObjectURL(url); }
    return { route, topics, topic, topicId, unitId, unit, loading, saving, error, notice, sections, queryText, sectionFilter, view, selectedId, selected, visibleUnits, visibleTopics, form, editing, editId, draft, draftUnit, tagText, previous, following, modalOpen, modalLabel, peerUnits, markdown, changeQuery, reload, newTopic, editTopic, sectionForm, unitForm, save, removeSection, removeTopic, removeUnit, dependencies, importFile, exportDraft, openUnit, closeModal, acceptDiscard, resetForm, unitPath, workspacePath, rememberWorkspace, switchTopic };
}
