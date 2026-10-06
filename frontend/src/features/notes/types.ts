export interface NoteSection {
    id: string;
    title: string;
    order: number;
}
export interface KnowledgeUnit {
    id: string;
    sectionId: string;
    title: string;
    content: string;
    tags: string[];
}
export interface DependencyEdge {
    fromUnitId: string;
    toUnitId: string;
}
export interface TopicData {
    title: string;
    description: string;
    sortOrder: number;
    preferredColumns: number;
    example: boolean;
    sections: NoteSection[];
    units: KnowledgeUnit[];
    edges: DependencyEdge[];
}
export interface NoteTopic extends TopicData {
    id: string;
    version: number;
}
export interface TopicSummary {
    id: string;
    version: number;
    title: string;
    description: string;
    sortOrder: number;
    sectionCount: number;
    unitCount: number;
}
