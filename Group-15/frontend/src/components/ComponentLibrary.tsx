import { useState, useEffect, useRef } from 'react';
import {
  Type,
  Square,
  Image as ImageIcon,
  Box,
  CreditCard,
  Heading,
  FolderInput as FormInput,
  Navigation,
  FileText,
  FileInput,
  Video,
  Grid3x3,
  List,
  Tag,
  Minus,
  Link as LinkIcon,
  MessageSquare,
  Search,
  Layout,
  Smile,
  Film,
  X,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { Component } from '../types';
import { createComponent } from '../utils/componentDefaults';
import { AssetService, Asset } from '../services/assetService';

interface ComponentLibraryProps {
  onAddComponent: (component: Component) => void;
}

type LibraryTab = 'components' | 'stickers' | 'photos' | 'gifs';

const COMPONENT_DEFS = [
  { type: 'heading' as const, icon: Heading, label: 'Heading', color: 'icon-blue' },
  { type: 'text' as const, icon: Type, label: 'Text', color: 'icon-violet' },
  { type: 'button' as const, icon: Square, label: 'Button', color: 'icon-pink' },
  { type: 'image' as const, icon: ImageIcon, label: 'Image', color: 'icon-green' },
  { type: 'input' as const, icon: FormInput, label: 'Input', color: 'icon-orange' },
  { type: 'textarea' as const, icon: MessageSquare, label: 'Textarea', color: 'icon-amber' },
  { type: 'card' as const, icon: CreditCard, label: 'Card', color: 'icon-teal' },
  { type: 'container' as const, icon: Box, label: 'Container', color: 'icon-sky' },
  { type: 'navbar' as const, icon: Navigation, label: 'Navbar', color: 'icon-cyan' },
  { type: 'footer' as const, icon: FileText, label: 'Footer', color: 'icon-emerald' },
  { type: 'form' as const, icon: FileInput, label: 'Form', color: 'icon-violet' },
  { type: 'video' as const, icon: Video, label: 'Video', color: 'icon-red' },
  { type: 'grid' as const, icon: Grid3x3, label: 'Grid', color: 'icon-pink' },
  { type: 'list' as const, icon: List, label: 'List', color: 'icon-green' },
  { type: 'badge' as const, icon: Tag, label: 'Badge', color: 'icon-rose' },
  { type: 'divider' as const, icon: Minus, label: 'Divider', color: 'icon-teal' },
  { type: 'link' as const, icon: LinkIcon, label: 'Link', color: 'icon-blue' },
];

export default function ComponentLibrary({ onAddComponent }: ComponentLibraryProps) {
  const [activeTab, setActiveTab] = useState<LibraryTab>('components');
  const [searchQuery, setSearchQuery] = useState('');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hoveredAsset, setHoveredAsset] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load trending stickers/photos when switching to asset tabs
  useEffect(() => {
    if (activeTab === 'stickers' && assets.length === 0 && !searchQuery) {
      loadTrending();
    }
  }, [activeTab]);

  // Debounced search
  useEffect(() => {
    if (activeTab === 'components') return;
    if (searchTimer.current) clearTimeout(searchTimer.current);

    if (!searchQuery) {
      if (activeTab === 'stickers' || activeTab === 'gifs') {
        loadTrending();
      }
      return;
    }

    searchTimer.current = setTimeout(() => {
      runSearch(searchQuery);
    }, 400);

    return () => {
      if (searchTimer.current) clearTimeout(searchTimer.current);
    };
  }, [searchQuery, activeTab]);

  const loadTrending = async () => {
    setIsLoading(true);
    try {
      const results = activeTab === 'gifs'
        ? await AssetService.searchGifs('trending')
        : await AssetService.getTrendingStickers();
      setAssets(results);
    } catch {
      setAssets([]);
    } finally {
      setIsLoading(false);
    }
  };

  const runSearch = async (q: string) => {
    setIsLoading(true);
    try {
      let results: Asset[] = [];
      if (activeTab === 'stickers') {
        results = await AssetService.searchStickers(q);
      } else if (activeTab === 'photos') {
        results = await AssetService.searchImages(q);
      } else if (activeTab === 'gifs') {
        results = await AssetService.searchGifs(q);
      }
      setAssets(results);
    } catch {
      setAssets([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTabChange = (tab: LibraryTab) => {
    setActiveTab(tab);
    setSearchQuery('');
    setAssets([]);
  };

  const handleDragStart = (e: React.DragEvent, type: Component['type']) => {
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('componentType', type);
  };

  const handleAssetDragStart = (e: React.DragEvent, asset: Asset) => {
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('componentType', 'image');
    e.dataTransfer.setData('assetUrl', asset.url);
  };

  const handleAssetClick = (asset: Asset) => {
    const component = createComponent('image');
    component.content = asset.url;
    // GIFs/stickers: transparent background, auto size
    if (asset.isGif) {
      component.styles.base = {
        ...component.styles.base,
        borderRadius: '0',
        boxShadow: 'none',
        background: 'transparent',
        objectFit: 'contain',
      };
    }
    onAddComponent(component);
  };

  const filteredComponents = COMPONENT_DEFS.filter(c =>
    c.label.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const tabs: { id: LibraryTab; icon: typeof Layout; label: string }[] = [
    { id: 'components', icon: Layout, label: 'Elements' },
    { id: 'stickers', icon: Smile, label: 'Stickers' },
    { id: 'photos', icon: ImageIcon, label: 'Photos' },
    { id: 'gifs', icon: Film, label: 'GIFs' },
  ];

  return (
    <div className="component-library">
      <div className="library-header">
        <div className="library-header-row">
          <Sparkles size={16} className="library-sparkle" />
          <h3>Library</h3>
        </div>
      </div>

      {/* Tabs */}
      <div className="library-tabs">
        {tabs.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            className={`tab-btn ${activeTab === id ? 'active' : ''}`}
            onClick={() => handleTabChange(id)}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="search-container">
        <div className="search-input-wrapper">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            placeholder={
              activeTab === 'components' ? 'Search elements...'
                : activeTab === 'stickers' ? 'Search stickers (coffee, cat, fire...)'
                  : activeTab === 'gifs' ? 'Search GIFs...'
                    : 'Search photos...'
            }
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="clear-search" onClick={() => setSearchQuery('')}>
              <X size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="library-content">

        {/* ── Components tab ── */}
        {activeTab === 'components' && (
          <div className="library-grid">
            {filteredComponents.map(({ type, icon: Icon, label, color }) => (
              <div
                key={type}
                className="library-item"
                draggable
                onDragStart={e => handleDragStart(e, type)}
                onClick={() => onAddComponent(createComponent(type))}
              >
                <div className={`library-item-icon ${color}`}>
                  <Icon size={20} />
                </div>
                <span>{label}</span>
              </div>
            ))}
          </div>
        )}

        {/* ── Stickers / Photos / GIFs tabs ── */}
        {activeTab !== 'components' && (
          <div className="assets-grid">
            {isLoading ? (
              <div className="loading-state">
                <Loader2 size={22} className="animate-spin" />
                <span>
                  {activeTab === 'stickers' ? 'Finding stickers...'
                    : activeTab === 'gifs' ? 'Loading GIFs...'
                      : 'Searching photos...'}
                </span>
              </div>
            ) : assets.length > 0 ? (
              <>
                {/* Header: trending label or result count */}
                <div className="asset-results-header">
                  {!searchQuery
                    ? <span>🔥 Trending {activeTab === 'gifs' ? 'GIFs' : activeTab === 'stickers' ? 'Stickers' : ''}</span>
                    : <span>{assets.length} results for "<strong>{searchQuery}</strong>"</span>
                  }
                </div>
                <div className="thumbnail-grid">
                  {assets.map(asset => (
                    <div
                      key={asset.id}
                      className={`asset-thumbnail ${asset.isGif ? 'gif-thumbnail' : ''}`}
                      draggable
                      onDragStart={e => handleAssetDragStart(e, asset)}
                      onClick={() => handleAssetClick(asset)}
                      onMouseEnter={() => setHoveredAsset(asset.id)}
                      onMouseLeave={() => setHoveredAsset(null)}
                      title={asset.alt}
                    >
                      <img
                        src={hoveredAsset === asset.id ? asset.url : asset.thumbnail}
                        alt={asset.alt}
                        loading="lazy"
                        style={asset.isGif ? { background: 'transparent', objectFit: 'contain' } : {}}
                      />
                      <div className="asset-overlay">
                        <ImageIcon size={14} />
                      </div>
                    </div>
                  ))}
                </div>
                {/* Powered-by badge for Giphy */}
                {(activeTab === 'stickers' || activeTab === 'gifs') && (
                  <div className="giphy-badge">
                    Powered by <strong>GIPHY</strong>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                {activeTab === 'stickers' ? <Smile size={32} /> : activeTab === 'gifs' ? <Film size={32} /> : <ImageIcon size={32} />}
                <p>
                  {searchQuery
                    ? `No results for "${searchQuery}"`
                    : activeTab === 'stickers' ? 'Search for stickers above'
                      : activeTab === 'gifs' ? 'Search for GIFs above'
                        : 'Search for photos above'}
                </p>
                <span>
                  {activeTab === 'stickers' || activeTab === 'gifs'
                    ? 'Try: coffee ☕  cat 🐱  celebrate 🎉  fire 🔥'
                    : 'Try: nature, city, technology, food'}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
