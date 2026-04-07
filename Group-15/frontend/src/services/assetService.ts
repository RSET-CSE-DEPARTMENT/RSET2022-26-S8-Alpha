export interface Asset {
    id: string;
    url: string;
    thumbnail: string;
    type: 'image' | 'sticker' | 'gif';
    alt: string;
    isGif?: boolean;
}

const GIPHY_API_KEY = 'gZC9k1NH0wUN6t1CvZkQwRSJsinWLSmQ';
const UNSPLASH_CLIENT_ID = 'v9pM6TfE7Q6m-fUvU0D5w6l6P2vW_z3G3B9u6v-C-6U';

export class AssetService {
    // ─── Giphy Stickers ──────────────────────────────────────────────────────────

    static async searchStickers(query: string): Promise<Asset[]> {
        try {
            const q = encodeURIComponent(query || 'happy');
            const url = `https://api.giphy.com/v1/stickers/search?api_key=${GIPHY_API_KEY}&q=${q}&limit=24&rating=g&lang=en`;
            const response = await fetch(url);

            if (!response.ok) {
                console.warn('Giphy sticker search failed, trying trending');
                return this.getTrendingStickers();
            }

            const data = await response.json();

            if (!data.data || data.data.length === 0) {
                return this.getTrendingStickers();
            }

            return data.data.map((item: any) => ({
                id: item.id,
                url: item.images.original.url,
                thumbnail: item.images.fixed_width_small.url || item.images.fixed_width.url,
                type: 'sticker',
                alt: item.title || 'Sticker',
                isGif: true,
            }));
        } catch (error) {
            console.error('Failed to search stickers:', error);
            return this.getTrendingStickers();
        }
    }

    static async getTrendingStickers(): Promise<Asset[]> {
        try {
            const url = `https://api.giphy.com/v1/stickers/trending?api_key=${GIPHY_API_KEY}&limit=24&rating=g`;
            const response = await fetch(url);
            const data = await response.json();

            return (data.data || []).map((item: any) => ({
                id: item.id,
                url: item.images.original.url,
                thumbnail: item.images.fixed_width_small.url || item.images.fixed_width.url,
                type: 'sticker',
                alt: item.title || 'Trending sticker',
                isGif: true,
            }));
        } catch {
            return [];
        }
    }

    // ─── Giphy GIFs ──────────────────────────────────────────────────────────────

    static async searchGifs(query: string): Promise<Asset[]> {
        try {
            const q = encodeURIComponent(query || 'funny');
            const url = `https://api.giphy.com/v1/gifs/search?api_key=${GIPHY_API_KEY}&q=${q}&limit=20&rating=g&lang=en`;
            const response = await fetch(url);

            if (!response.ok) return [];

            const data = await response.json();
            return (data.data || []).map((item: any) => ({
                id: item.id,
                url: item.images.original.url,
                thumbnail: item.images.fixed_width_small.url || item.images.fixed_width.url,
                type: 'gif',
                alt: item.title || 'GIF',
                isGif: true,
            }));
        } catch (error) {
            console.error('Failed to search GIFs:', error);
            return [];
        }
    }

    // ─── Unsplash Photos ─────────────────────────────────────────────────────────

    static async searchImages(query: string): Promise<Asset[]> {
        try {
            const response = await fetch(
                `https://api.unsplash.com/search/photos?query=${encodeURIComponent(query)}&per_page=20&client_id=${UNSPLASH_CLIENT_ID}`
            );

            if (!response.ok) {
                return this.getPexelsImages(query);
            }

            const data = await response.json();
            return (data.results || []).map((item: any) => ({
                id: item.id,
                url: item.urls.regular,
                thumbnail: item.urls.small || item.urls.thumb,
                type: 'image',
                alt: item.alt_description || item.description || query,
            }));
        } catch {
            return this.getPexelsImages(query);
        }
    }

    // Fallback: Picsum (no key needed, random but works reliably)
    private static getPexelsImages(query: string): Asset[] {
        return Array.from({ length: 12 }, (_, i) => ({
            id: `pexels-${i}`,
            url: `https://picsum.photos/seed/${encodeURIComponent(query)}-${i}/800/600`,
            thumbnail: `https://picsum.photos/seed/${encodeURIComponent(query)}-${i}/300/200`,
            type: 'image',
            alt: `${query} photo ${i + 1}`,
        }));
    }
}
