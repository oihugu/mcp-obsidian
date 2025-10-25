# Fase 2: Navegação Semântica - Plano de Implementação

**Data:** 2025-10-25
**Status:** 🚧 **PLANEJAMENTO**

---

## 📊 Visão Geral

Implementar busca semântica e análise de relacionamentos entre notas usando embeddings vetoriais. O sistema permitirá:
- Buscar notas por significado, não apenas palavras-chave
- Descobrir notas relacionadas automaticamente
- Sugerir links entre notas
- Analisar relacionamentos no vault

---

## 🏗️ Arquitetura

### Componentes Principais

```
src/mcp_obsidian/semantic/
├── __init__.py
├── embeddings.py      # Geração e gerenciamento de embeddings
├── search.py          # Busca por similaridade vetorial
├── relationships.py   # Análise de relacionamentos
└── links.py           # Sugestão de links
```

### Fluxo de Dados

```
Nota markdown
    ↓
Extração de texto (sem frontmatter)
    ↓
Geração de embedding (sentence-transformers)
    ↓
Armazenamento vetorial (FAISS)
    ↓
Busca por similaridade / Análise de relacionamentos
    ↓
Resultados ranqueados
```

---

## 🔧 Dependências Novas

```toml
dependencies = [
    "mcp>=1.1.0",
    "python-dotenv>=1.0.1",
    "requests>=2.32.3",
    "sentence-transformers>=2.2.2",  # Embeddings locais
    "faiss-cpu>=1.7.4",               # Busca vetorial
    "numpy>=1.24.0",                  # Operações vetoriais
]
```

**Modelo de Embedding:**
- `all-MiniLM-L6-v2` (384 dimensões)
- Leve (~80MB)
- Bom equilíbrio entre performance e tamanho
- Multilingual support

---

## 📦 Módulos a Implementar

### 1. `semantic/embeddings.py` - EmbeddingsManager

**Responsabilidades:**
- Gerar embeddings para notas
- Cache de embeddings em disco
- Gerenciar modelo sentence-transformers
- Rebuild do índice quando necessário

**Métodos principais:**
```python
class EmbeddingsManager:
    def __init__(self, cache_dir: str, model_name: str)
    def generate_embedding(self, text: str) -> np.ndarray
    def generate_note_embedding(self, filepath: str, content: str) -> Dict
    def batch_generate_embeddings(self, notes: List[Dict]) -> List[Dict]
    def load_cache(self) -> Dict[str, np.ndarray]
    def save_cache(self, embeddings: Dict[str, np.ndarray])
    def clear_cache()
```

**Cache Format (JSON):**
```json
{
  "People/Igor Curi.md": {
    "embedding": [0.123, -0.456, ...],
    "hash": "abc123...",
    "timestamp": "2025-10-25T10:30:00"
  }
}
```

### 2. `semantic/search.py` - SemanticSearchEngine

**Responsabilidades:**
- Construir índice FAISS
- Busca por similaridade
- Filtros adicionais (pasta, tags, tipo)

**Métodos principais:**
```python
class SemanticSearchEngine:
    def __init__(self, embeddings_manager: EmbeddingsManager)
    def build_index(self, notes: List[Dict])
    def search(self, query: str, top_k: int, filters: Dict) -> List[Dict]
    def search_by_note(self, filepath: str, top_k: int) -> List[Dict]
    def get_similar_notes(self, embedding: np.ndarray, top_k: int) -> List[Dict]
```

**Resultado de busca:**
```python
{
    "filepath": "People/Igor Curi.md",
    "similarity": 0.89,
    "title": "Igor Curi",
    "snippet": "Trabalha no projeto CNI...",
    "tags": ["besolution", "colleague"]
}
```

### 3. `semantic/relationships.py` - RelationshipAnalyzer

**Responsabilidades:**
- Identificar clusters de notas relacionadas
- Analisar relacionamentos entre entidades (pessoas, projetos)
- Detectar temas comuns

**Métodos principais:**
```python
class RelationshipAnalyzer:
    def __init__(self, search_engine: SemanticSearchEngine)
    def find_related_notes(self, filepath: str, threshold: float) -> List[Dict]
    def analyze_note_clusters(self, min_similarity: float) -> List[List[str]]
    def get_vault_graph(self) -> Dict[str, List[str]]
    def find_bridge_notes(self) -> List[Dict]  # Notas que conectam clusters
```

**Exemplo de clusters:**
```python
[
    {
        "theme": "CNI Project",
        "notes": ["People/Igor Curi.md", "Projetos/BeSolution/CNI - Chatbot.md"],
        "avg_similarity": 0.85
    }
]
```

### 4. `semantic/links.py` - LinkSuggestionEngine

**Responsabilidades:**
- Sugerir links para adicionar em notas
- Detectar menções não linkadas
- Priorizar sugestões por relevância

**Métodos principais:**
```python
class LinkSuggestionEngine:
    def __init__(self, relationship_analyzer: RelationshipAnalyzer)
    def suggest_links_for_note(self, filepath: str, max_suggestions: int) -> List[Dict]
    def find_unlinked_mentions(self, filepath: str) -> List[Dict]
    def suggest_bidirectional_links(self, filepath: str) -> List[Dict]
```

**Formato de sugestão:**
```python
{
    "target": "People/Igor Curi.md",
    "reason": "semantic_similarity",
    "similarity": 0.87,
    "snippet": "mencionado no contexto de...",
    "suggestion": "Adicionar link [[Igor Curi]] no contexto de 'reunião'"
}
```

---

## 🛠️ Novos Tools MCP

### Tool 1: `obsidian_semantic_search`

Busca notas por significado semântico.

**Parâmetros:**
- `query` (required): Texto da busca
- `top_k`: Número de resultados (padrão: 10, max: 50)
- `folder`: Filtrar por pasta
- `include_content`: Incluir snippet de conteúdo
- `min_similarity`: Similaridade mínima (0-1)

**Exemplo:**
```json
{
  "tool": "obsidian_semantic_search",
  "args": {
    "query": "projetos de inteligência artificial e chatbots",
    "top_k": 5,
    "folder": "Projetos",
    "min_similarity": 0.7
  }
}
```

### Tool 2: `obsidian_find_related_notes`

Encontra notas semanticamente relacionadas a uma nota específica.

**Parâmetros:**
- `filepath` (required): Caminho da nota de referência
- `top_k`: Número de resultados (padrão: 10)
- `min_similarity`: Similaridade mínima (padrão: 0.6)
- `include_content`: Incluir snippet

**Exemplo:**
```json
{
  "tool": "obsidian_find_related_notes",
  "args": {
    "filepath": "People/Igor Curi.md",
    "top_k": 5,
    "min_similarity": 0.7
  }
}
```

### Tool 3: `obsidian_suggest_links`

Sugere links para adicionar em uma nota.

**Parâmetros:**
- `filepath` (required): Caminho da nota
- `max_suggestions`: Número de sugestões (padrão: 10)
- `min_similarity`: Similaridade mínima (padrão: 0.7)
- `check_existing`: Não sugerir links já existentes (padrão: true)

**Exemplo:**
```json
{
  "tool": "obsidian_suggest_links",
  "args": {
    "filepath": "Projetos/BeSolution/CNI - Chatbot.md",
    "max_suggestions": 5,
    "min_similarity": 0.75
  }
}
```

### Tool 4: `obsidian_analyze_relationships`

Analisa relacionamentos no vault ou em uma pasta.

**Parâmetros:**
- `folder`: Pasta para analisar (opcional, padrão: vault completo)
- `min_similarity`: Similaridade mínima para relacionamento (padrão: 0.7)
- `find_clusters`: Encontrar clusters de notas (padrão: true)
- `find_bridges`: Encontrar notas que conectam clusters (padrão: false)

**Exemplo:**
```json
{
  "tool": "obsidian_analyze_relationships",
  "args": {
    "folder": "People",
    "min_similarity": 0.75,
    "find_clusters": true
  }
}
```

### Tool 5: `obsidian_rebuild_embeddings`

Reconstrói o índice de embeddings (para novas notas ou atualizações).

**Parâmetros:**
- `force`: Forçar rebuild completo (padrão: false, incremental)
- `folder`: Rebuild apenas em pasta específica (opcional)

**Exemplo:**
```json
{
  "tool": "obsidian_rebuild_embeddings",
  "args": {
    "force": false
  }
}
```

---

## 💾 Estrutura de Cache

### Localização
```
.mcp-obsidian/
├── embeddings-cache.json        # Embeddings + metadata
├── faiss-index.bin              # Índice FAISS
└── index-metadata.json          # Metadata do índice
```

### embeddings-cache.json
```json
{
  "model": "all-MiniLM-L6-v2",
  "dimension": 384,
  "notes": {
    "People/Igor Curi.md": {
      "embedding": [...],
      "hash": "abc123",
      "timestamp": "2025-10-25T10:30:00"
    }
  }
}
```

### index-metadata.json
```json
{
  "total_notes": 110,
  "last_rebuild": "2025-10-25T10:30:00",
  "model": "all-MiniLM-L6-v2",
  "note_paths": ["People/Igor Curi.md", ...],
  "folders_indexed": ["People", "Projetos", "Daily Notes"]
}
```

---

## 🎯 Algoritmos

### 1. Geração de Embedding para Nota

```python
def generate_note_embedding(filepath: str, content: str) -> np.ndarray:
    # 1. Extrair frontmatter
    fm, body = extract_frontmatter(content)

    # 2. Limpar markdown (remover links, formatação)
    clean_text = clean_markdown(body)

    # 3. Construir texto contextual
    # Incluir título e tags do frontmatter para melhor contexto
    title = fm.get('name') or fm.get('project') or Path(filepath).stem
    tags = ' '.join(fm.get('tags', []))

    text = f"{title}\n\n{tags}\n\n{clean_text}"

    # 4. Gerar embedding
    embedding = model.encode(text, normalize_embeddings=True)

    return embedding
```

### 2. Busca Semântica

```python
def semantic_search(query: str, top_k: int) -> List[Dict]:
    # 1. Gerar embedding da query
    query_embedding = model.encode(query, normalize_embeddings=True)

    # 2. Buscar no índice FAISS
    distances, indices = faiss_index.search(
        query_embedding.reshape(1, -1),
        top_k
    )

    # 3. Converter distâncias para similaridade
    # FAISS retorna L2 distance, converter para cosine similarity
    similarities = 1 - (distances / 2)

    # 4. Construir resultados
    results = []
    for idx, similarity in zip(indices[0], similarities[0]):
        note = get_note_by_index(idx)
        results.append({
            "filepath": note['path'],
            "similarity": float(similarity),
            "title": note['title'],
            "snippet": generate_snippet(note['content'], query)
        })

    return results
```

### 3. Detecção de Clusters

```python
def find_clusters(min_similarity: float = 0.75) -> List[List[str]]:
    # 1. Calcular matriz de similaridade
    similarity_matrix = compute_pairwise_similarities()

    # 2. Aplicar threshold
    adjacency = similarity_matrix > min_similarity

    # 3. Encontrar componentes conectados (clusters)
    clusters = connected_components(adjacency)

    return clusters
```

### 4. Sugestão de Links

```python
def suggest_links(filepath: str, max_suggestions: int) -> List[Dict]:
    # 1. Encontrar notas relacionadas
    related = find_related_notes(filepath, top_k=20)

    # 2. Filtrar notas já linkadas
    existing_links = extract_existing_links(filepath)
    candidates = [r for r in related if r['path'] not in existing_links]

    # 3. Analisar contexto textual
    content = get_note_content(filepath)
    suggestions = []

    for candidate in candidates[:max_suggestions]:
        # Verificar se há menção textual
        mentions = find_text_mentions(content, candidate['title'])

        suggestions.append({
            "target": candidate['path'],
            "similarity": candidate['similarity'],
            "mentions": mentions,
            "reason": "semantic_similarity" if not mentions else "unlinked_mention"
        })

    return sorted(suggestions, key=lambda x: x['similarity'], reverse=True)
```

---

## 📋 Implementação em Etapas

### Etapa 1: Setup e Embeddings
- [ ] Adicionar dependências ao pyproject.toml
- [ ] Criar estrutura de diretórios
- [ ] Implementar EmbeddingsManager
- [ ] Testar geração de embeddings

### Etapa 2: Busca Semântica
- [ ] Implementar SemanticSearchEngine
- [ ] Integrar FAISS
- [ ] Criar tool `obsidian_semantic_search`
- [ ] Testar busca básica

### Etapa 3: Relacionamentos
- [ ] Implementar RelationshipAnalyzer
- [ ] Criar tool `obsidian_find_related_notes`
- [ ] Criar tool `obsidian_analyze_relationships`
- [ ] Testar análise de clusters

### Etapa 4: Sugestão de Links
- [ ] Implementar LinkSuggestionEngine
- [ ] Criar tool `obsidian_suggest_links`
- [ ] Testar sugestões

### Etapa 5: Gerenciamento de Índice
- [ ] Implementar rebuild incremental
- [ ] Criar tool `obsidian_rebuild_embeddings`
- [ ] Otimizar performance

### Etapa 6: Testes e Documentação
- [ ] Criar suite de testes completa
- [ ] Testar com vault remoto
- [ ] Atualizar FEATURES.md
- [ ] Criar exemplos de uso

---

## 🔍 Considerações Técnicas

### Performance

**Vault pequeno (<100 notas):**
- Rebuild completo: ~10-30 segundos
- Busca: <100ms

**Vault médio (100-1000 notas):**
- Rebuild completo: ~1-5 minutos
- Busca: <200ms

**Vault grande (>1000 notas):**
- Rebuild completo: ~5-15 minutos
- Busca: <500ms
- Considerar FAISS GPU

### Estratégias de Otimização

1. **Cache inteligente**: Hash do conteúdo para detectar mudanças
2. **Rebuild incremental**: Só reprocessar notas modificadas
3. **Lazy loading**: Carregar embeddings sob demanda
4. **Batch processing**: Processar múltiplas notas em paralelo

### Limitações

1. **Modelo local**: all-MiniLM-L6-v2 é bom mas não perfeito
   - Alternativa futura: OpenAI embeddings (requer API key)
2. **Idioma**: Modelo tem melhor performance em inglês
   - Mas tem suporte multilingual razoável
3. **Contexto**: Embeddings capturam conteúdo geral, não nuances

---

## 🎨 Casos de Uso

### Caso 1: Descobrir Projetos Relacionados
```
Usuário tem nota sobre "CNI - Chatbot"
→ obsidian_find_related_notes
→ Descobre "CNI - Detran" e "Podcast Generator MCP"
→ Todos envolvem IA e chatbots
```

### Caso 2: Encontrar Pessoas para um Projeto
```
Usuário cria novo projeto sobre "Machine Learning"
→ obsidian_semantic_search "expertise em machine learning"
→ Encontra pessoas que trabalharam em projetos de ML
→ Pode adicioná-las ao time
```

### Caso 3: Melhorar Conectividade do Vault
```
→ obsidian_analyze_relationships (vault completo)
→ Identifica notas isoladas
→ Para cada nota isolada:
  → obsidian_suggest_links
  → Adiciona links sugeridos
→ Vault mais conectado e navegável
```

### Caso 4: Busca Inteligente
```
Usuário procura: "reuniões sobre arquitetura de software"
→ obsidian_semantic_search
→ Encontra:
  - Daily notes com reuniões
  - Notas de projetos com discussões de arquitetura
  - Não precisa ter exatamente essas palavras
```

---

## 📊 Métricas de Sucesso

- [ ] Busca semântica retorna resultados relevantes (>70% precision)
- [ ] Relacionamentos detectados fazem sentido (validação manual)
- [ ] Sugestões de links são úteis (>50% aceitas pelo usuário)
- [ ] Performance aceitável (busca <500ms em vault médio)
- [ ] Cache reduz rebuild time em >80%

---

## 🚀 Próximos Passos Após Fase 2

### Fase 3: Templates Inteligentes
- Templates contextuais baseados em similaridade
- Auto-aplicação de templates

### Fase 5: Recursos MCP Avançados
- Resources navegáveis para embeddings
- Prompts pré-configurados para busca semântica

---

**Preparado por:** Claude Code
**Status:** Pronto para implementação
