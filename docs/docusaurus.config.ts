import { themes as prismThemes } from 'prism-react-renderer';
import type { Config } from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'MOON SPA Documentation',
  tagline: 'Python Framework for Single Page Applications',
  favicon: 'img/favicon.svg',

  future: {
    v4: true,
  },

  url: 'https://moon-spa.dev',
  baseUrl: '/',

  organizationName: 'moon-spa',
  projectName: 'moon-spa',

  onBrokenLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: '/docs',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  markdown: {
    mermaid: true,
  },

  themes: ['@docusaurus/theme-mermaid'],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    mermaid: {
      theme: { light: 'neutral', dark: 'dark' },
    },
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'MOON-SPA',
      logo: {
        alt: 'moon-spa logo',
        src: 'img/moon-spa-logo.png',
        srcDark: 'img/moon-spa-logo.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          type: 'docSidebar',
          sidebarId: 'apiSidebar',
          position: 'left',
          label: 'API',
        },
        {
          href: 'https://github.com/roderiano/moon-spa',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            { label: 'Get Started', to: '/docs/get-started/installation' },
            { label: 'Guide', to: '/docs/guide/components' },
            { label: 'API Reference', to: '/docs/api/framework' },
          ],
        },
        {
          title: 'Community',
          items: [
            { label: 'GitHub', href: 'https://github.com/roderiano/moon-spa' },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} moon-spa. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['python', 'bash', 'json'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;