import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

interface RuntimeBundleManifest {
  runtime_root: string
  bundled_repo_root: string
  bundled_python: {
    root: string
    executable: string
  }
  bundled_node: {
    root: string
    executable: string
  }
  include: string[]
  exclude_globs: string[]
}

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))

function loadManifest(): RuntimeBundleManifest {
  const manifestPath = path.resolve(TEST_DIR, '../runtime-manifest.json')
  return JSON.parse(readFileSync(manifestPath, 'utf-8')) as RuntimeBundleManifest
}

function loadPackageJson(): {
  scripts: Record<string, string>
} {
  const packagePath = path.resolve(TEST_DIR, '../package.json')
  return JSON.parse(readFileSync(packagePath, 'utf-8')) as { scripts: Record<string, string> }
}

function loadTauriConfig(): {
  build: { beforeBuildCommand: string }
  bundle: { resources?: Record<string, string> | string[] }
} {
  const configPath = path.resolve(TEST_DIR, '../src-tauri/tauri.conf.json')
  return JSON.parse(readFileSync(configPath, 'utf-8')) as {
    build: { beforeBuildCommand: string }
    bundle: { resources?: Record<string, string> | string[] }
  }
}

describe('desktop runtime bundle manifest', () => {
  it('defines a stable packaged runtime layout', () => {
    const manifest = loadManifest()

    expect(manifest.runtime_root).toBe('ordo-runtime')
    expect(manifest.bundled_repo_root).toBe('repo')
    expect(manifest.bundled_python.root).toBe('python')
    expect(manifest.bundled_python.executable).toBe('python/bin/python3')
    expect(manifest.bundled_node.root).toBe('node')
    expect(manifest.bundled_node.executable).toBe('node/bin/node')
  })

  it('includes the minimum engine files required by the packaged desktop app', () => {
    const manifest = loadManifest()
    const requiredEntries = [
      'scripts/workbench_bridge.py',
      'publish.py',
      'publish_console_state.py',
      'markdown_utils.py',
      'live_cdp.mjs',
      'live_cdp_ws_resolver.mjs',
      'zhihu_publisher.py',
      'toutiao_publisher.py',
      'yidian_publisher.py',
      'jianshu_publisher.py',
      'tiandi_engine',
      'themes',
      'templates',
    ]

    for (const entry of requiredEntries) {
      expect(manifest.include).toContain(entry)
    }
  })

  it('keeps docs, tests and local caches out of the packaged runtime', () => {
    const manifest = loadManifest()

    expect(manifest.exclude_globs).toEqual(
      expect.arrayContaining([
        '**/__pycache__/**',
        '**/*.pyc',
        'tests/**',
        'docs/**',
        '.tiandidistribute/**',
        '.worktrees/**',
      ]),
    )
  })

  it('references only files that currently exist in the repository', () => {
    const manifest = loadManifest()
    const repoRoot = path.resolve(TEST_DIR, '../..')

    for (const entry of manifest.include) {
      expect(existsSync(path.join(repoRoot, entry))).toBe(true)
    }
  })

  it('runs runtime preparation before tauri build and bundles the generated runtime directory', () => {
    const pkg = loadPackageJson()
    const tauriConfig = loadTauriConfig()

    expect(pkg.scripts['prepare:runtime']).toBeTruthy()
    expect(tauriConfig.build.beforeBuildCommand).toContain('prepare:runtime')
    expect(tauriConfig.bundle.resources).toEqual(
      expect.objectContaining({
        '../runtime-dist/ordo-runtime/repo/': 'ordo-runtime/repo/',
        '../runtime-dist/ordo-runtime/python/': 'ordo-runtime/python/',
        '../runtime-dist/ordo-runtime/runtime-metadata.json': 'ordo-runtime/runtime-metadata.json',
        '../runtime-dist/ordo-runtime/node-runtime.tar.gz': 'ordo-runtime/node-runtime.tar.gz',
      }),
    )
  })
})
