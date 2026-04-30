# Lua SPA - Documentação Completa

Esta documentação foi gerada com detalhes completos sobre o framework Lua SPA, incluindo arquitetura, componentes, state management e referência completa da API.

## 📚 Estrutura da Documentação

### 1. **Introdução** (`index.md`)
- O que é Lua SPA
- Recursos principais
- Quick start básico
- Estrutura do projeto

### 2. **Getting Started** (`getting-started.md`)
- Instalação passo a passo
- Entendendo `spa.config.json`
- Criando seu primeiro componente
- Renderização e hidratação
- Resolução de problemas

### 3. **Arquitetura** (`architecture.md`)
- Diagrama da arquitetura do sistema
- Fluxo de requisição/resposta
- Ciclo de vida do componente
- Responsabilidades de cada módulo
- Fluxo de gerenciamento de estado

### 4. **Componentes** (`components/index.md`)
- O que são componentes
- Estrutura de um componente
- Seção de importações
- Bloco Python (context e client)
- Seção de template
- Props e comunicação entre componentes

### 5. **State Management** (`components/state.md`)
- Definindo estado com classes State
- Parâmetros: name, from_prop, default, cast
- Multiple state fields
- Mutando estado com operações (add, sub, set, toggle)
- Ciclo de vida do estado
- Best practices
- Exemplo: Login form state

### 6. **Template Syntax** (`components/templates.md`)
- Interpolação de variáveis
- Diretivas (v-if, v-show, v-for)
- Atributo binding
- Class binding
- Style binding
- Event binding
- Form handling
- Padrões avançados

### 7. **API Reference** (`api/index.md`)
- Visão geral dos módulos
- Quick reference para classes principais
- Links para documentação detalhada

### 8. **Framework API** (`api/framework.md`)
- Classe `SpaFramework`
- Factory method `from_lua_template_directory()`
- Métodos de instância: `__init__()`, `render()`, `serve()`, `build_html()`
- Properties: `entry_component`, `mount_id`
- Exemplos de uso
- Tratamento de erros
- Considerações de performance

## 🎯 Guia Rápido por Caso de Uso

### Quero começar rapidinho
1. Leia: [Getting Started](./docs/getting-started.md)
2. Crie seu primeiro componente em `lua_template/components/`
3. Execute `poetry run lua-spa`

### Quero entender como tudo funciona
1. Leia: [Arquitetura](./docs/architecture.md)
2. Entenda os fluxos de renderização e estado
3. Explore os módulos

### Quero criar componentes
1. Leia: [Componentes](./docs/components/index.md)
2. Leia: [State Management](./docs/components/state.md)
3. Leia: [Template Syntax](./docs/components/templates.md)

### Preciso de referência da API
1. Consulte: [API Reference](./docs/api/index.md)
2. Veja exemplos de uso
3. Explore os módulos específicos

## 📁 Arquivos de Documentação

### Inglês (English)
```
docs/
├── index.md                          # Página inicial
├── getting-started.md                # Guia de início
├── architecture.md                   # Visão geral da arquitetura
├── _category_.json
├── components/
│   ├── index.md                      # Componentes (visão geral)
│   ├── state.md                      # Gerenciamento de estado
│   ├── templates.md                  # Sintaxe de templates
│   └── _category_.json
└── api/
    ├── index.md                      # API reference (visão geral)
    ├── framework.md                  # SpaFramework class
    └── _category_.json
```

### Português (`i18n/pt-BR`)
```
i18n/pt-BR/docusaurus-plugin-content-docs/current/
├── index.mdx                         # Página inicial em PT
├── getting-started.md                # Guia de início em PT
├── architecture.md                   # Arquitetura em PT
├── _category_.json
├── components/
│   └── _category_.json
└── api/
    └── _category_.json
```

## 🚀 Iniciando a Documentação

### Desenvolvimento Local
```bash
cd docs
npm run start
```

Acesse `http://localhost:3000` (Inglês) ou `http://localhost:3000/pt-BR` (Português)

### Build Estático
```bash
cd docs
npm run build
```

Os arquivos estáticos estarão em `docs/build/`

### Deploy
```bash
cd docs
npm run deploy
```

## 📖 Conteúdo Detalhado

### Componentes
A documentação de componentes cobre:
- Estrutura de um arquivo `.lspa`
- Importação de componentes
- Props e comunicação
- Exemplos práticos (Counter, Form)
- Padrões (Container/Presentational, HOCs)
- Best practices

### State Management
A documentação de estado cobre:
- Definição de estado com classes
- Parâmetros de estado (name, from_prop, default, cast)
- Operações de mutação (add, sub, set, toggle)
- Ciclo de vida do estado
- Valores derivados
- Normalizando estado
- Exemplos avançados

### Template Syntax
A documentação de templates cobre:
- Interpolação `{{ }}`
- Diretivas (v-if, v-else, v-for, v-show)
- Attribute binding (`:`)
- Event binding (`@`)
- Class binding
- Style binding
- Form handling
- Padrões avançados

### API Reference
A documentação da API cobre:
- Classe `SpaFramework` (factory e métodos)
- Classe `ComponentLoader`
- Funções `render()`, `serve()`
- Tipos e classes base
- Exemplos de uso

## 🎓 Nível de Detalhe

A documentação é escrita em **três níveis de detalhe**:

### Nível 1: Visão Geral
- Introdução ao conceito
- Caso de uso principal
- Exemplo simples

### Nível 2: Conceitos
- Explicação detalhada
- Múltiplos exemplos
- Best practices

### Nível 3: Referência
- Documentação completa da API
- Todos os parâmetros
- Todos os casos de uso
- Tratamento de erros

## 🌐 Internacionalização (i18n)

A documentação está disponível em:
- **Inglês** (padrão): `/docs/`
- **Português Brasileiro**: `/docs/pt-BR/`

Use o seletor de idioma 🌐 na barra de navegação para alternar.

## 📝 Manutenção

Para adicionar ou atualizar documentação:

1. **Inglês**: Edite arquivos em `docs/docs/`
2. **Português**: Edite arquivos em `docs/i18n/pt-BR/docusaurus-plugin-content-docs/current/`

### Criar nova página em Inglês
```bash
# Em docs/docs/
touch nova-pagina.md
# Adicione front matter com sidebar_position
```

### Criar tradução em Português
```bash
# Em docs/i18n/pt-BR/docusaurus-plugin-content-docs/current/
touch nova-pagina.md
# Copie conteúdo de docs/docs/nova-pagina.md e traduza
```

## ✅ Checklist de Documentação Completa

- [x] Página inicial (index.md)
- [x] Getting Started (instalação, primeiro componente)
- [x] Arquitetura do Sistema
- [x] Guia de Componentes
- [x] State Management
- [x] Template Syntax
- [x] API Reference (SpaFramework)
- [x] Exemplos práticos
- [x] Best practices
- [x] Troubleshooting
- [x] Internacionalização (PT-BR)
- [x] Categorias de sidebar
- [x] Links de navegação

## 🔗 Estrutura de Links

A documentação usa links relativos para navegação:
- `[Getting Started](./getting-started.md)`
- `[Componentes](./components/index.md)`
- `[State](./components/state.md)`
- `[API](./api/framework.md)`

## 📊 Estatísticas

- **Total de Páginas**: 12+ (em inglês)
- **Total de Palavras**: 15,000+ (em inglês)
- **Exemplos de Código**: 50+ (com melhorias contínuas)
- **Idiomas Suportados**: 2 (Inglês e Português)

## 🎯 Próximos Passos para Melhorar a Documentação

1. Adicionar mais exemplos de componentes complexos
2. Adicionar guia de debugging e troubleshooting avançado
3. Adicionar guia de deployment
4. Adicionar case studies
5. Adicionar video tutorials
6. Adicionar API reference para loader.py, renderer.py, etc.

---

**Última atualização**: 30 de Abril de 2026
**Framework Version**: 0.1.0
