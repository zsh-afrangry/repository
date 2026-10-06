from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Section(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=120)
    order: int = Field(ge=0, le=100000)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError("名称不能为空")
        return value.strip()


class Unit(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    sectionId: str
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(max_length=1000000)
    tags: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError("标题不能为空")
        return value.strip()

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, values):
        if any(not v.strip() or len(v) > 64 for v in values):
            raise ValueError("标签不能为空且不超过64字")
        return list(dict.fromkeys(v.strip() for v in values))


class Edge(StrictModel):
    fromUnitId: str
    toUnitId: str


class TopicData(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    sortOrder: int = Field(default=0, ge=0, le=100000)
    preferredColumns: int = Field(default=3, ge=1, le=6)
    example: bool = False
    sections: list[Section] = Field(default_factory=list, max_length=200)
    units: list[Unit] = Field(default_factory=list, max_length=2000)
    edges: list[Edge] = Field(default_factory=list, max_length=20000)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError("主题名称不能为空")
        return value.strip()

    @model_validator(mode="after")
    def validate_graph(self):
        if sum(len(u.content.encode("utf-8")) for u in self.units) > 5_000_000:
            raise ValueError("单个主题正文总量不能超过5MB，请拆分主题")
        sections = {s.id for s in self.sections}
        units = {u.id for u in self.units}
        if len(sections) != len(self.sections) or len(units) != len(self.units):
            raise ValueError("目录或单元 ID 重复")
        if any(u.sectionId not in sections for u in self.units):
            raise ValueError("单元必须属于本主题的有效目录")
        adjacency = {uid: [] for uid in units}
        degree = {uid: 0 for uid in units}
        seen = set()
        for edge in self.edges:
            a, b = edge.fromUnitId, edge.toUnitId
            if a not in units or b not in units:
                raise ValueError("依赖只能引用本主题内存在的知识单元")
            if a == b:
                raise ValueError("不能依赖自己")
            if (a, b) in seen:
                raise ValueError("依赖关系重复")
            seen.add((a, b))
            adjacency[a].append(b)
            degree[b] += 1
        queue = [u for u in units if degree[u] == 0]
        count = 0
        while queue:
            a = queue.pop()
            count += 1
            for b in adjacency[a]:
                degree[b] -= 1
                if degree[b] == 0:
                    queue.append(b)
        if count != len(units):
            # Explain one actual cycle without recursive traversal (large graphs are valid input).
            completed = set()
            titles = {u.id: u.title for u in self.units}
            for root in units:
                if root in completed:
                    continue
                trail = [root]
                positions = {root: 0}
                stack = [(root, iter(adjacency[root]))]
                while stack:
                    node, children = stack[-1]
                    child = next(children, None)
                    if child is None:
                        stack.pop()
                        positions.pop(node)
                        trail.pop()
                        completed.add(node)
                    elif child in positions:
                        cycle = trail[positions[child]:] + [child]
                        label = " → ".join(titles[u] for u in cycle[:8])
                        if len(cycle) > 8:
                            label += " → …"
                        raise ValueError(f"依赖关系形成循环：{label}")
                    elif child not in completed:
                        positions[child] = len(trail)
                        trail.append(child)
                        stack.append((child, iter(adjacency[child])))
            raise ValueError("依赖关系形成循环")
        return self


class TopicUpdate(TopicData):
    version: int = Field(ge=1)
