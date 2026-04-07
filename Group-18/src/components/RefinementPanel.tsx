import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { supabase } from "@/integrations/supabase/client";
import { format } from "date-fns";
import { addSessionLog, LogActionType } from "@/lib/logging";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

export interface RefinementState {
  x: number;
  y: number;
  scale: number;
  scaleX?: number;
  scaleY?: number;
  rotate: number;
}

export type ComponentLayer = "face" | "eyes" | "nose" | "mouth" | "hair" | "beard";

interface RefinementPanelProps {
  selectedLayer: ComponentLayer;
  onLayerChange: (layer: ComponentLayer) => void;
  refinement: RefinementState;
  onRefinementChange: (state: RefinementState) => void;
}

const components: { value: ComponentLayer; label: string }[] = [
  { value: "face", label: "CRANIAL BASE" },
  { value: "hair", label: "HAIR STRUCTURE" },
  { value: "beard", label: "FACIAL HAIR" },
  { value: "eyes", label: "OCULAR REGION" },
  { value: "nose", label: "NASAL STRUCTURE" },
  { value: "mouth", label: "ORAL REGION" },
];

type Log = {
  id: string;
  action_type: LogActionType;
  description: string;
  timestamp: string;
};

export const RefinementPanel = ({ 
  selectedLayer, 
  onLayerChange,
  refinement, 
  onRefinementChange
}: RefinementPanelProps) => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [refinementText, setRefinementText] = useState("");
  const [logs, setLogs] = useState<Log[]>([]);
  const [lockAspect, setLockAspect] = useState<boolean>(true);
  const [isRefining, setIsRefining] = useState(false);
  const BASE_CANVAS = 512; 

  useEffect(() => {
    if (sessionId) fetchLogs();
  }, [sessionId]);

  const fetchLogs = async () => {
    if (!sessionId) return;
    const { data, error } = await supabase
      .from('logs')
      .select('*')
      .eq('session_id', sessionId)
      .order('timestamp', { ascending: false });

    if (!error && data) {
      setLogs(data as Log[]);
    }
  };

  const addLog = async (actionType: LogActionType, desc: string) => {
    if (!sessionId) return;
    await addSessionLog(sessionId, actionType, desc);
    fetchLogs();
  };

  const handleChange = (key: keyof RefinementState, val: number) => {
    if (key === 'scale') {
      onRefinementChange({ ...refinement, scale: val, scaleX: val, scaleY: val });
    } else {
      onRefinementChange({ ...refinement, [key]: val } as any);
    }
  };

  const handleReset = () => {
    onRefinementChange({ x: 0, y: 0, scale: 1, rotate: 0 });
    toast.info(`SYSTEM: ${selectedLayer.toUpperCase()} PARAMETERS RESET.`);
    addLog('reset', `[${selectedLayer.toUpperCase()}] Parameters reverted to baseline.`);
  };

  const handleApplyTextRefinement = () => {
    if (!refinementText.trim()) return;
    
    const lower = refinementText.toLowerCase();
    let newRefinement = { ...refinement };
    let actionTaken = false;

    if (lower.includes('bigger') || lower.includes('larger') || lower.includes('increase')) {
      newRefinement.scale = Math.min(2, newRefinement.scale + 0.1);
      actionTaken = true;
    }
    if (lower.includes('smaller') || lower.includes('decrease')) {
      newRefinement.scale = Math.max(0.5, newRefinement.scale - 0.1);
      actionTaken = true;
    }
    if (lower.includes('up') || lower.includes('higher')) {
      newRefinement.y = Math.max(-150, newRefinement.y - 15);
      actionTaken = true;
    }
    if (lower.includes('down') || lower.includes('lower')) {
      newRefinement.y = Math.min(150, newRefinement.y + 15);
      actionTaken = true;
    }
    if (lower.includes('left')) {
      newRefinement.x = Math.max(-100, newRefinement.x - 15);
      actionTaken = true;
    }
    if (lower.includes('right')) {
      newRefinement.x = Math.min(100, newRefinement.x + 15);
      actionTaken = true;
    }
    if (lower.includes('rotate left') || lower.includes('counter')) {
      newRefinement.rotate = Math.max(-45, newRefinement.rotate - 5);
      actionTaken = true;
    }
    if (lower.includes('rotate right') || lower.includes('clockwise') || lower.match(/rotate/)) {
      newRefinement.rotate = Math.min(45, newRefinement.rotate + 5);
      actionTaken = true;
    }

    if (actionTaken) {
      onRefinementChange(newRefinement);
      toast.success(`SMART REFINE APPLIED TO ${selectedLayer.toUpperCase()}.`);
      addLog('text_refine', `[${selectedLayer.toUpperCase()}] NLP Directive: "${refinementText}"`);
    } else {
      toast.info("DIRECTIVE UNCLEAR. USE 'MOVE UP', 'MAKE BIGGER', ETC.");
    }
    setRefinementText("");
  };

  const handleApplyScaling = async () => {
    const scaleX = refinement.scaleX ?? refinement.scale ?? 1;
    const scaleY = refinement.scaleY ?? refinement.scale ?? 1;
    
    if (scaleX === 1 && scaleY === 1) {
      toast.info("NO SCALING DETECTED. ADJUST DIMENSIONS FIRST.");
      return;
    }
    if (selectedLayer === 'face') {
      toast.warning("CRANIAL BASE CANNOT BE RE-SYNTHESIZED. SELECT A FEATURE.");
      return;
    }

    setIsRefining(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:7860'}/refine-feature`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: selectedLayer, scaleX, scaleY, sessionId })
      });

      let result = await response.json();

      if (result.status === "success") {
        toast.success(`RE-SYNTHESIS COMPLETE: ${selectedLayer.toUpperCase()}`);
        addLog('regenerate', `[${selectedLayer.toUpperCase()}] Neural Re-synthesis applied.`);
      } else {
        toast.error("RE-SYNTHESIS FAULT.");
      }
    } catch (error) {
      toast.error("NETWORK ERROR: NEURAL ENGINE UNREACHABLE.");
    } finally {
      setIsRefining(false);
    }
  };

  const handleSave = async () => {
    if (!sessionId) return;
    await supabase.from('sessions').update({ status: 'Completed' }).eq('id', sessionId);
    toast.success("CASE RECORD SECURED.");
    addLog('save', `Session marked as Completed and secured.`);
  };

  return (
    <div className="flex flex-col h-full bg-card p-3 shadow-inner overflow-hidden">
      <div className="flex items-center justify-between border-b border-border pb-2 shrink-0">
        <h2 className="text-xs font-bold uppercase tracking-widest text-primary">Refinement Toolkit</h2>
        <Button variant="outline" size="sm" onClick={handleReset} className="h-6 text-[9px] font-mono tracking-widest rounded-sm px-2">
          [ RESET ]
        </Button>
      </div>

      <Tabs defaultValue="toolkit" className="flex-1 flex flex-col min-h-0 mt-2">
        <TabsList className="grid w-full grid-cols-2 h-8 shrink-0 bg-background border border-border rounded-sm">
          <TabsTrigger value="toolkit" className="text-[10px] uppercase font-bold tracking-widest rounded-sm">Parameters</TabsTrigger>
          <TabsTrigger value="history" className="text-[10px] uppercase font-bold tracking-widest rounded-sm">Audit Log</TabsTrigger>
        </TabsList>

        <TabsContent value="toolkit" className="flex-1 flex flex-col min-h-0 mt-3 space-y-3">
          <div className="space-y-1.5 shrink-0">
            <label className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">Target Feature</label>
            <Select value={selectedLayer} onValueChange={(v) => onLayerChange(v as ComponentLayer)}>
              <SelectTrigger className="h-8 bg-background border-border text-[10px] font-mono uppercase rounded-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {components.map((comp) => (
                  <SelectItem key={comp.value} value={comp.value} className="text-[10px] font-mono uppercase">
                    {comp.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-2 shrink-0">
            <div className="space-y-1.5 bg-secondary/30 p-2 border border-border rounded-sm">
              <div className="flex justify-between items-center text-[9px] font-bold text-muted-foreground uppercase tracking-widest">
                <span>X-Axis</span>
                <span className="font-mono text-primary">{refinement.x}</span>
              </div>
              <Slider value={[refinement.x]} onValueChange={(v) => handleChange('x', v[0])} min={-100} max={100} step={1} className="h-3" />
            </div>

            <div className="space-y-1.5 bg-secondary/30 p-2 border border-border rounded-sm">
              <div className="flex justify-between items-center text-[9px] font-bold text-muted-foreground uppercase tracking-widest">
                <span>Y-Axis</span>
                <span className="font-mono text-primary">{refinement.y}</span>
              </div>
              <Slider value={[refinement.y]} onValueChange={(v) => handleChange('y', v[0])} min={-150} max={150} step={1} className="h-3" />
            </div>

            <div className="space-y-1.5 bg-secondary/30 p-2 border border-border rounded-sm">
              <div className="flex justify-between items-center text-[9px] font-bold text-muted-foreground uppercase tracking-widest">
                <span>Scale</span>
                <span className="font-mono text-primary">{Math.round((refinement.scale || 1) * 100)}%</span>
              </div>
              <Slider value={[(refinement.scale || 1) * 100]} onValueChange={(v) => handleChange('scale', v[0] / 100)} min={50} max={200} step={1} className="h-3" />
            </div>

            <div className="space-y-1.5 bg-secondary/30 p-2 border border-border rounded-sm">
              <div className="flex justify-between items-center text-[9px] font-bold text-muted-foreground uppercase tracking-widest">
                <span>Rotate</span>
                <span className="font-mono text-primary">{refinement.rotate}°</span>
              </div>
              <Slider value={[refinement.rotate]} onValueChange={(v) => handleChange('rotate', v[0])} min={-45} max={45} step={1} className="h-3" />
            </div>
          </div>

          <div className="flex items-center justify-between bg-secondary/30 p-2 border border-border rounded-sm shrink-0">
            <label className="inline-flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={lockAspect} onChange={(e) => setLockAspect(e.target.checked)} className="rounded-sm bg-background border-border" />
              <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground">Lock Aspect Ratio</span>
            </label>
            {!lockAspect && (
              <div className="flex gap-2">
                <Input 
                  type="number" 
                  className="h-6 w-14 text-[10px] px-1 font-mono rounded-sm" 
                  placeholder="W"
                  value={Math.round(((refinement.scaleX ?? refinement.scale) || 1) * BASE_CANVAS)}
                  onChange={(e) => {
                    const w = Number(e.target.value) || 0;
                    const scaleX = Math.max(0.1, Math.min(4, w / BASE_CANVAS));
                    handleChange('scaleX', scaleX);
                  }}
                />
                <Input 
                  type="number" 
                  className="h-6 w-14 text-[10px] px-1 font-mono rounded-sm" 
                  placeholder="H"
                  value={Math.round(((refinement.scaleY ?? refinement.scale) || 1) * BASE_CANVAS)}
                  onChange={(e) => {
                    const h = Number(e.target.value) || 0;
                    const scaleY = Math.max(0.1, Math.min(4, h / BASE_CANVAS));
                    handleChange('scaleY', scaleY);
                  }}
                />
              </div>
            )}
          </div>

          <div className="space-y-1.5 shrink-0 pt-2 border-t border-border">
            <label className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">NLP Micro-Adjustment</label>
            <div className="flex gap-2">
              <Input
                placeholder="E.G., 'MAKE NOSE HIGHER'"
                value={refinementText}
                onChange={(e) => setRefinementText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleApplyTextRefinement()}
                className="h-8 text-[10px] font-mono uppercase rounded-sm bg-background"
              />
              <Button onClick={handleApplyTextRefinement} size="sm" className="h-8 text-[9px] font-bold tracking-widest rounded-sm px-3">
                [ APPLY ]
              </Button>
            </div>
          </div>

          {selectedLayer !== 'face' && (!lockAspect || (refinement.scale !== 1)) && (
            <Button 
              onClick={handleApplyScaling} 
              disabled={isRefining}
              className="w-full h-8 text-[10px] font-bold tracking-widest uppercase rounded-sm shrink-0 border border-primary bg-primary/10 text-primary hover:bg-primary/20"
            >
              {isRefining ? "EXECUTING..." : "EXECUTE GAN RESYNTHESIS"}
            </Button>
          )}

          <div className="mt-auto pt-2 shrink-0 border-t border-border">
            <Button variant="secondary" onClick={handleSave} className="w-full h-9 text-[10px] font-bold tracking-widest uppercase rounded-sm">
              [ SECURE CASE RECORD ]
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="history" className="flex-1 overflow-y-auto mt-2 pr-1 space-y-2 pb-2">
          {logs.length === 0 ? (
            <p className="text-[10px] text-center text-muted-foreground font-mono mt-4">NO AUDIT RECORDS FOUND.</p>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="p-2 rounded-sm bg-secondary/20 border border-border">
                <div className="flex justify-between items-start mb-1">
                  <p className="text-[9px] font-bold text-primary uppercase tracking-widest">{log.action_type}</p>
                  <p className="text-[8px] text-muted-foreground font-mono">{format(new Date(log.timestamp), 'HH:mm:ss')}</p>
                </div>
                <p className="text-[10px] font-mono leading-tight text-foreground/80">{log.description}</p>
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};