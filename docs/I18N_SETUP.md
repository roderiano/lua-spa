# Configuração de Internacionalização (i18n)

Este projeto Docusaurus está configurado com suporte completo para **Inglês (en)** e **Português Brasileiro (pt-BR)**.

## Estrutura de Diretórios

```
docs/
├── docs/                                # Documentos em inglês (padrão)
│   ├── intro.mdx
│   ├── tutorial-basics/
│   └── tutorial-extras/
├── i18n/
│   └── pt-BR/                          # Traduções para português
│       ├── code.json                   # Strings da UI traduzidas
│       ├── docusaurus-theme-classic/   # Traduções do tema
│       │   ├── navbar.json
│       │   ├── footer.json
│       │   └── sidebar.json
│       └── docusaurus-plugin-content-docs/
│           └── current/                # Documentos em português
│               ├── intro.mdx
│               ├── tutorial-basics/
│               └── tutorial-extras/
└── docusaurus.config.ts                # Configuração principal
```

## Adicionar Novos Conteúdos

### Adicionar um documento em Inglês
1. Crie o arquivo em `docs/` com a estrutura apropriada
2. Exemplo: `docs/guides/getting-started.md`

### Adicionar uma tradução em Português
1. Crie o arquivo correspondente em `i18n/pt-BR/docusaurus-plugin-content-docs/current/`
2. Mantenha a mesma estrutura de pastas
3. Exemplo: `i18n/pt-BR/docusaurus-plugin-content-docs/current/guides/getting-started.md`

## Traduzir Strings da Interface

As strings da UI são traduzidas em `i18n/pt-BR/code.json`. Você pode adicionar mais traduções conforme necessário:

```json
{
  "theme.docs.sidebar.toggle": "Alternar barra lateral",
  "theme.docs.sidebar.collapseCategories": "Colapsar categorias"
}
```

## Comandos Úteis

```bash
# Iniciar servidor de desenvolvimento
npm run start

# Gerar arquivo de traduções base
npm run write-translations

# Construir para produção
npm run build

# Servir site construído localmente
npm run serve
```

## Acessar Diferentes Idiomas

- **Inglês**: `http://localhost:3000`
- **Português**: `http://localhost:3000/pt-BR`

Use o seletor de idioma no canto superior direito da barra de navegação para alternar entre idiomas.

## Configuração de i18n

A configuração de i18n está em [docusaurus.config.ts](./docusaurus.config.ts):

```typescript
i18n: {
  defaultLocale: 'en',
  locales: ['en', 'pt-BR'],
  path: 'i18n',
  localeConfigs: {
    en: {
      label: 'English',
      direction: 'ltr',
      htmlLang: 'en-US',
    },
    'pt-BR': {
      label: 'Português (Brasil)',
      direction: 'ltr',
      htmlLang: 'pt-BR',
    },
  },
},
```

## Referências

- [Documentação oficial de i18n do Docusaurus](https://docusaurus.io/docs/i18n/introduction)
- [Markdown features](https://docusaurus.io/docs/markdown-features)
- [Sidebar configuration](https://docusaurus.io/docs/sidebar)
