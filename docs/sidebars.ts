import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'category',
      label: 'Get Started',
      items: [
        'get-started/installation',
        'get-started/quick-start',
        'get-started/project-structure',
        'get-started/first-component',
        'get-started/routing',
      ],
    },
    {
      type: 'category',
      label: 'Guide',
      items: [
        'guide/components',
        'guide/state',
        'guide/actions',
        'guide/props',
        'guide/computed',
        'guide/lifecycle',
        'guide/templating',
        'guide/hydration',
        'guide/dom-diff',
        'guide/backend-integration',
        'guide/routing',
      ],
    },
    {
      type: 'category',
      label: 'Advanced',
      items: [
        'advanced/architecture',
        'advanced/rendering-engine',
        'advanced/template-parser',
        'advanced/code-generator',
        'advanced/performance',
      ],
    },
    {
      type: 'category',
      label: 'Examples',
      items: [
        'examples/counter',
        'examples/form-handling',
        'examples/dynamic-list',
        'examples/server-data',
        'examples/routing',
      ],
    },
    {
      type: 'category',
      label: 'Community',
      items: [
        'contributing',
        'philosophy',
      ],
    },
  ],

  apiSidebar: [
    {
      type: 'category',
      label: 'API Reference',
      items: [
        'api/framework',
        'api/component',
        'api/router',
        'api/cli',
        'api/config',
      ],
    },
  ],
};

export default sidebars;
