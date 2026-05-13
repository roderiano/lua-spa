import type { ReactNode } from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <header className={clsx(styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className={styles.heroTitle}>
          {siteConfig.title}
        </Heading>
        <p className={styles.heroSubtitle}>{siteConfig.tagline}</p>
        <p className={styles.heroTagline}>
          Combine the power of Server Rendering with Client Hydration —<br />
          build modern, fast SPAs with pure Python. No JavaScript build step.
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--primary button--lg"
            to="/docs/get-started/installation">
            Get Started →
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/docs/guide/components"
            style={{ marginLeft: '1rem' }}>
            Read the Guide
          </Link>
        </div>
        <div className={styles.install}>
          <code>pip install moon-spa</code>
        </div>
      </div>
    </header>
  );
}

const features = [
  {
    title: '🐍 Pure Python',
    description: 'Write component logic in Python. The framework generates all the JavaScript for you.',
  },
  {
    title: '⚡ SSR + Hydration',
    description: 'Every page is server-rendered HTML. JavaScript takes over seamlessly for interactivity.',
  },
  {
    title: '🔌 No Build Step',
    description: 'No webpack, no npm, no TypeScript. pip install and start building.',
  },
  {
    title: '🧩 Component System',
    description: '.lspa files combine template, Python, and CSS in one place. Import and compose freely.',
  },
  {
    title: '🗺️ Built-in Router',
    description: 'Nested routes, dynamic params, wildcard fallbacks — configured in spa.config.json.',
  },
  {
    title: '♻️ Hot Reload',
    description: 'Run with --reload and the browser refreshes automatically on any file change.',
  },
];

export default function Home(): ReactNode {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="Python Framework for Single Page Applications">
      <HomepageHeader />
      <main>
        <section className={styles.features}>
          <div className="container">
            <div className={styles.featureGrid}>
              {features.map((f) => (
                <div key={f.title} className={styles.featureCard}>
                  <h3>{f.title}</h3>
                  <p>{f.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
