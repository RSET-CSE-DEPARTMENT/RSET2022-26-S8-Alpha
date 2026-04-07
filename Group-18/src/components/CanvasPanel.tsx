import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ComponentLayer, RefinementState } from "./RefinementPanel";

// --- Types ---
// (Removed local definitions, now imported from RefinementPanel)

interface CanvasPanelProps {
  caseId: string;
  realismScore: number;
  hasSketch: boolean;
  faceShape?: string;
  eyeImage: string | null;   // Layer 1: Eyes
  noseImage: string | null;  // Layer 2: Nose
  mouthImage: string | null; // Layer 3: Mouth
  hairImage: string | null;  // Layer 4: Hair
  beardImage?: string | null; // Layer 5: Beard (Optional for backward compatibility)
  allRefinements: Record<ComponentLayer, RefinementState>;
}

export const CanvasPanel = ({ 
  caseId, 
  realismScore, 
  hasSketch, 
  faceShape = "oval", 
  eyeImage, 
  noseImage,
  mouthImage,
  hairImage,
  beardImage,
  allRefinements
}: CanvasPanelProps) => {
  const [zoom, setZoom] = useState(100);
  const [imgError, setImgError] = useState(false);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 10, 200));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 10, 50));
  const handleReset = () => setZoom(100);

  // Helper to generate precise CSS transform for each specific layer
  const getLayerStyle = (layer: ComponentLayer) => {
    // Fallback if a refinement doesn't exist yet for a new layer like beard
    const r = allRefinements[layer] || { x: 0, y: 0, scale: 1, rotate: 0 };
    
    const sx = r.scaleX ?? r.scale ?? 1;
    const sy = r.scaleY ?? r.scale ?? 1;
    return {
      transform: `translate(${r.x}px, ${r.y}px) scale(${sx}, ${sy}) rotate(${r.rotate}deg)`,
      transformOrigin: "center center", // CRITICAL: Forces CSS math to exactly match OpenCV matrix math
      // Z-Index Protocol (Matches OpenCV blend order): Face(10) -> Beard(15) -> Eyes(20) -> Nose(25) -> Mouth(30) -> Hair(35)
      zIndex: layer === 'face' ? 10 :
              layer === 'beard' ? 15 :
              layer === 'eyes' ? 20 : 
              layer === 'nose' ? 25 : 
              layer === 'mouth' ? 30 : 35
    };
  };

  const getBaseFaceSrc = (shape: string) => {
    switch (shape?.toLowerCase()) {
      case 'round': return '/faces/round_face.png';
      case 'square': return '/faces/square_face.png';
      case 'long': return '/faces/long_face.png';
      default: return '/faces/oval_face.png';
    }
  };

  return (
    <div className="flex flex-col h-full bg-card p-3 shadow-inner overflow-hidden border border-border rounded-sm">
      
      {/* HEADER SECTION */}
      <div className="flex items-center justify-between border-b border-border pb-2 shrink-0">
        <div className="flex gap-6">
          <div>
            <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">Case Identifier</span>
            <p className="text-xs font-mono font-bold text-primary">{caseId || "UNASSIGNED"}</p>
          </div>
          <div>
            <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">Integrity Index</span>
            <p className="text-xs font-mono font-bold text-accent">{realismScore}%</p>
          </div>
        </div>
        <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
          OPTICS: {zoom}%
        </div>
      </div>

      {/* MAIN CANVAS VIEWPORT */}
      <div className="flex-1 min-h-0 bg-secondary/10 border border-border my-2 flex items-center justify-center relative overflow-hidden bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:20px_20px]">
        <div 
          className="transition-transform duration-300 origin-center relative flex items-center justify-center"
          style={{ transform: `scale(${zoom / 100})` }}
        >
          {/* THE FORENSIC RECONSTRUCTION BOARD (Fixed 512x512 constraint) */}
          <div className="w-[300px] h-[300px] md:w-[400px] md:h-[400px] lg:w-[512px] lg:h-[512px] bg-white border border-border relative shadow-2xl overflow-hidden shrink-0">
            
            {/* LAYER 0: BASE CRANIAL TEMPLATE */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={getLayerStyle('face')}>
                {!imgError ? (
                  <img 
                    src={getBaseFaceSrc(faceShape)} 
                    alt={`${faceShape} face outline`}
                    className="w-full h-full object-contain opacity-40 transition-transform duration-200"
                    onError={() => setImgError(true)}
                  />
                ) : (
                  // CSS Structural Fallback if image is missing
                  <div 
                    className="border-4 border-gray-300 opacity-40"
                    style={{
                      width: faceShape === 'round' ? '70%' : faceShape === 'square' ? '65%' : '60%',
                      height: faceShape === 'round' ? '70%' : faceShape === 'square' ? '75%' : '85%',
                      borderRadius: faceShape === 'square' ? '60px' : '50%'
                    }}
                  />
                )}
            </div>

            {/* LAYER 1: FACIAL HAIR / BEARD (Z: 15) */}
            {beardImage && (
              <img 
                src={beardImage} 
                alt="Generated Beard" 
                className="absolute top-0 left-0 w-full h-full object-cover mix-blend-multiply transition-transform duration-200"
                style={getLayerStyle('beard')}
              />
            )}

            {/* LAYER 2: OCULAR REGION (Z: 20) */}
            {eyeImage && (
              <img 
                src={eyeImage} 
                alt="Generated Eyes" 
                className="absolute top-0 left-0 w-full h-full object-cover mix-blend-multiply transition-transform duration-200"
                style={getLayerStyle('eyes')}
              />
            )}

            {/* LAYER 3: NASAL STRUCTURE (Z: 25) */}
            {noseImage && (
              <img 
                src={noseImage} 
                alt="Generated Nose" 
                className="absolute top-0 left-0 w-full h-full object-cover mix-blend-multiply transition-transform duration-200"
                style={getLayerStyle('nose')}
              />
            )}

            {/* LAYER 4: ORAL REGION (Z: 30) */}
            {mouthImage && (
              <img 
                src={mouthImage} 
                alt="Generated Mouth" 
                className="absolute top-0 left-0 w-full h-full object-cover mix-blend-multiply transition-transform duration-200"
                style={getLayerStyle('mouth')}
              />
            )}

            {/* LAYER 5: HAIR STRUCTURE (Z: 35) */}
            {hairImage && (
              <img 
                src={hairImage} 
                alt="Generated Hair" 
                className="absolute top-0 left-0 w-full h-full object-cover mix-blend-multiply transition-transform duration-200"
                style={getLayerStyle('hair')}
              />
            )}

            {/* NULL STATE / AWAITING DATA */}
            {(!eyeImage && !mouthImage && !noseImage && !hairImage && !beardImage && !hasSketch) && (
                <div className="absolute inset-0 flex items-center justify-center z-0">
                  <p className="text-muted-foreground text-[10px] font-mono uppercase tracking-widest bg-black/5 px-4 py-2 rounded-sm border border-black/10">
                    AWAITING NEURAL GENERATION...
                  </p>
                </div>
            )}
          </div>
        </div>
      </div>

      {/* FOOTER OPTICS CONTROLS */}
      <div className="flex items-center justify-center gap-2 shrink-0 pt-2 border-t border-border">
        <Button variant="outline" size="sm" onClick={handleZoomOut} disabled={zoom <= 50} className="h-8 text-[9px] font-bold tracking-widest uppercase rounded-sm px-4">
          [ ZOOM OUT ]
        </Button>
        <Button variant="outline" size="sm" onClick={handleReset} className="h-8 text-[9px] font-bold tracking-widest uppercase rounded-sm px-4">
          [ 1:1 RESET ]
        </Button>
        <Button variant="outline" size="sm" onClick={handleZoomIn} disabled={zoom >= 200} className="h-8 text-[9px] font-bold tracking-widest uppercase rounded-sm px-4">
          [ ZOOM IN ]
        </Button>
      </div>
    </div>
  );
};