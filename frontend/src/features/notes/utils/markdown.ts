import { marked } from 'marked';
import DOMPurify from 'dompurify';
/** GFM block parsing precedes inline emphasis; code and lists keep their boundaries. */
export function renderNoteMarkdown(content: string): string {
    const clean = DOMPurify.sanitize(marked.parse(content, { async: false, gfm: true }), {
        FORBID_TAGS: ['style', 'iframe', 'form', 'input', 'button', 'textarea', 'select'],
        FORBID_ATTR: ['style', 'id', 'name'],
    });
    const template = document.createElement('template');
    template.innerHTML = clean;
    for (const table of template.content.querySelectorAll('table')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'prose-table-scroll';
        wrapper.tabIndex = 0;
        wrapper.setAttribute('role', 'region');
        wrapper.setAttribute('aria-label', '表格，可横向滚动');
        table.replaceWith(wrapper);
        wrapper.append(table);
    }
    for (const pre of template.content.querySelectorAll('pre')) {
        pre.tabIndex = 0;
        pre.setAttribute('aria-label', '代码块，可横向滚动');
    }
    for (const link of template.content.querySelectorAll('a'))
        link.setAttribute('rel', 'noopener noreferrer');
    return template.innerHTML;
}
/** Deliberately supports title and inline tags only, rejecting unsupported YAML rather than losing it. */
export function importNoteMarkdown(raw: string, filename: string) {
    let content = raw.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
    let title = filename.replace(/\.md$/i, '') || '导入笔记';
    let tags: string[] = [];
    if (content.startsWith('---\n')) {
        const end = content.indexOf('\n---\n', 4);
        if (end < 0)
            throw new Error('Frontmatter 缺少结束标记 ---');
        const scalar = (s: string) => s.trim().replace(/^(["'])(.*)\1$/, '$2');
        for (const line of content.slice(4, end).split('\n').filter(s => s.trim() && !s.trim().startsWith('#'))) {
            if (line.startsWith('title:'))
                title = scalar(line.slice(6));
            else if (/^tags:\s*\[.*\]\s*$/.test(line))
                tags = line.slice(line.indexOf('[') + 1, line.lastIndexOf(']')).split(',').map(scalar).filter(Boolean);
            else
                throw new Error('目前 Frontmatter 仅支持 title 和 tags: [标签1, 标签2]，请调整后重试；原文件未修改');
        }
        content = content.slice(end + 5).replace(/^\n/, '');
    }
    return { title, tags, content };
}
