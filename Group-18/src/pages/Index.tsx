import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { InputPanel } from "@/components/InputPanel";
import { CanvasPanel } from "@/components/CanvasPanel";
import { RefinementPanel, RefinementState, ComponentLayer } from "@/components/RefinementPanel";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { addSessionLog } from "@/lib/logging";
import { Progress } from "@/components/ui/progress";
import { jsPDF } from "jspdf";

const API_BASE_URL = import.meta.env.DEV 
  ? "http://127.0.0.1:7860" 
  : "https://arunvjo04-smart-forensic-backend.hf.space";

interface Message {
  sender: 'user' | 'bot';
  text: string;
}

const INITIAL_REFINEMENTS: Record<ComponentLayer, RefinementState> = {
  face: { x: 0, y: 0, scale: 1, rotate: 0 },
  hair: { x: 0, y: -40, scale: 1.1, rotate: 0 },
  eyes: { x: 0, y: -50, scale: 1, rotate: 0 },
  nose: { x: 0, y: 15, scale: 1, rotate: 0 },
  mouth: { x: 0, y: 70, scale: 1, rotate: 0 },
  beard: { x: 0, y: 100, scale: 1, rotate: 0 }
};

type WorkspacePhase = "setup" | "editing" | "blended" | "enhanced" | "validated";

const Index = () => {
  const { sessionId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  
  const IMAGES_STORAGE_KEY = sessionId ? `forensic-images-${sessionId}` : "";
  const [phase, setPhase] = useState<WorkspacePhase>("setup");
  
  const [hasSketch, setHasSketch] = useState(false);
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [suspectName, setSuspectName] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);

  const [finalBlendedImage, setFinalBlendedImage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState<number>(0);
  const [validationResult, setValidationResult] = useState<{match: string, confidence: number} | null>(null);

  const [history, setHistory] = useState<Array<{ image: string | null; timestamp: number }>>([]);
  const [redoStack, setRedoStack] = useState<Array<{ image: string | null; timestamp: number }>>([]);

  const INTERVIEW_FLOW: ComponentLayer[] = ['eyes', 'nose', 'mouth', 'hair'];
  const [interviewStage, setInterviewStage] = useState<number>(0);
  const [interviewActive, setInterviewActive] = useState<boolean>(false);

  const [faceShape, setFaceShape] = useState<string>("oval");
  const [gender, setGender] = useState<string>("male");
  const [ageGroup, setAgeGroup] = useState<string>("young");

  const [eyeImage, setEyeImage] = useState<string | null>(null);
  const [mouthImage, setMouthImage] = useState<string | null>(null);
  const [noseImage, setNoseImage] = useState<string | null>(null);
  const [hairImage, setHairImage] = useState<string | null>(null);
  const [beardImage, setBeardImage] = useState<string | null>(null);

  const [activeLayer, setActiveLayer] = useState<ComponentLayer>("eyes");
  const [allRefinements, setAllRefinements] = useState<Record<ComponentLayer, RefinementState>>(INITIAL_REFINEMENTS);

  const hasFetched = useRef(false);
  const isFirstPrompt = useRef(true);

  const syncToDatabase = async (overrideData?: any) => {
    if (!sessionId) return;
    try {
      const payload = {
        session_id: sessionId,
        face_shape: overrideData?.faceShape ?? faceShape,
        gender: overrideData?.gender ?? gender,
        age_group: overrideData?.ageGroup ?? ageGroup,
        suspect_name: overrideData?.suspectName ?? suspectName,
        eye_image: overrideData?.eyeImage ?? eyeImage,
        nose_image: overrideData?.noseImage ?? noseImage,
        mouth_image: overrideData?.mouthImage ?? mouthImage,
        hair_image: overrideData?.hairImage ?? hairImage,
        refinements: overrideData?.allRefinements ?? allRefinements,
        final_image: overrideData?.finalBlendedImage ?? finalBlendedImage,
        workspace_phase: overrideData?.phase ?? phase
      };
      await supabase.from('composite_faces').upsert([payload], { onConflict: 'session_id' });
    } catch (error) {
      console.error("Silent DB Sync Failed:", error);
    }
  };

  const handleUndo = async () => {
    if (history.length === 0) return;
    const lastState = history[history.length - 1];
    setRedoStack(prev => [...prev, { image: finalBlendedImage, timestamp: Date.now() }]);
    setFinalBlendedImage(lastState.image);
    setHistory(prev => prev.slice(0, -1));
    toast.success("REVERTED TO PREVIOUS STATE.");
  };

  const handleRedo = async () => {
    if (redoStack.length === 0) return;
    const nextState = redoStack[redoStack.length - 1];
    setHistory(prev => [...prev, { image: finalBlendedImage, timestamp: Date.now() }]);
    setFinalBlendedImage(nextState.image);
    setRedoStack(prev => prev.slice(0, -1));
    toast.success("STATE RESTORED.");
  };

  const handleConfirmNext = async () => {
    const nextStage = interviewStage + 1;
    if (nextStage < INTERVIEW_FLOW.length) {
      setInterviewStage(nextStage);
      const nextLayer = INTERVIEW_FLOW[nextStage];
      setActiveLayer(nextLayer);
      toast.info(`SYSTEM: FOCUS SHIFTED TO ${nextLayer.toUpperCase()}.`);
      return `Describe the ${nextLayer} in detail.`;
    } else {
      setInterviewActive(false);
      setInterviewStage(0);
      toast.success("INTERVIEW PROTOCOL COMPLETE.");
      return "";
    }
  };

  const handleStartInterview = () => {
    setInterviewActive(true);
    setInterviewStage(0);
    setActiveLayer('eyes');
    toast.info("INTERVIEW PROTOCOL INITIATED.");
  };

  useEffect(() => {
    // Only save if we aren't loading and have a valid key
    if (typeof window !== "undefined" && IMAGES_STORAGE_KEY && !loading) {
      try {
        const stateToSave = {
          faceShape, suspectName, gender, ageGroup,
          // Optional: You could save only the refinements to save space, 
          // as images should ideally come from Supabase.
          eyeImage, mouthImage, noseImage, hairImage, beardImage, 
          refinements: allRefinements, 
          finalBlendedImage, 
          phase
        };
        
        window.localStorage.setItem(IMAGES_STORAGE_KEY, JSON.stringify(stateToSave));
      } catch (error) {
        if (error instanceof DOMException && error.name === 'QuotaExceededError') {
          console.warn("⚠️ LocalStorage quota exceeded. Sketch state will rely on Supabase database only.");
          // Clear old keys to try and make room if necessary
          // window.localStorage.clear(); 
        } else {
          console.error("Failed to save to localStorage:", error);
        }
      }
    }
  }, [faceShape, suspectName, gender, ageGroup, eyeImage, mouthImage, noseImage, hairImage, beardImage, allRefinements, finalBlendedImage, phase, IMAGES_STORAGE_KEY, loading]);

  useEffect(() => {
    if (!authLoading && !user) navigate('/auth');
  }, [user, authLoading, navigate]);

  useEffect(() => {
    if (sessionId && user?.id && !hasFetched.current) {
      fetchSession();
      hasFetched.current = true;
    }
    return () => { hasFetched.current = false; };
  }, [sessionId, user?.id]);

  const fetchSession = async () => {
    setLoading(true);
    const { data: sessionData, error: sessionError } = await supabase
      .from('sessions')
      .select('*')
      .eq('id', sessionId)
      .maybeSingle();

    if (sessionError) {
      toast.error('CRITICAL: FAILED TO LOAD SESSION DATA.');
      navigate('/dashboard');
      return;
    }
    
    setSession(sessionData);

    const { data } = await supabase
      .from('composite_faces')
      .select('*')
      .eq('session_id', sessionId)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();
      
    const faceData = data as any;

    if (faceData) {
      setFaceShape(faceData.face_shape || "oval");
      setGender(faceData.gender || "male");
      setAgeGroup(faceData.age_group || "young");
      setSuspectName(faceData.suspect_name || "");
      setEyeImage(faceData.eye_image || null);
      setNoseImage(faceData.nose_image || null);
      setMouthImage(faceData.mouth_image || null);
      setHairImage(faceData.hair_image || null);
      setBeardImage(faceData.beard_image || null);
      if (faceData.refinements) setAllRefinements(faceData.refinements);
      
      const hasAnyFeature = !!(faceData.eye_image || faceData.nose_image || faceData.mouth_image || faceData.hair_image);
      setHasSketch(hasAnyFeature);
      isFirstPrompt.current = !hasAnyFeature;

      if (faceData.workspace_phase) {
        setPhase(faceData.workspace_phase);
      } else if (faceData.final_image) {
        setFinalBlendedImage(faceData.final_image);
        setPhase("blended");
      } else if (hasAnyFeature) {
        setPhase("editing");
      } else {
        setPhase("setup");
      }
    } else {
      const stored = typeof window !== "undefined" && window.localStorage.getItem(IMAGES_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setFaceShape(parsed.faceShape);
        setGender(parsed.gender);
        setAgeGroup(parsed.ageGroup);
        setSuspectName(parsed.suspectName);
        setEyeImage(parsed.eyeImage);
        setNoseImage(parsed.noseImage);
        setMouthImage(parsed.mouthImage);
        setHairImage(parsed.hairImage);
        setBeardImage(parsed.beardImage || null);
        setAllRefinements(parsed.refinements || INITIAL_REFINEMENTS);
        setFinalBlendedImage(parsed.finalBlendedImage);
        
        const hasAnyFeature = !!(parsed.eyeImage || parsed.noseImage || parsed.mouthImage || parsed.hairImage);
        if (parsed.phase) {
          setPhase(parsed.phase);
        } else if (parsed.finalBlendedImage) {
          setPhase("blended");
        } else if (hasAnyFeature) {
          setPhase("editing");
        } else {
          setPhase("setup");
        }
        
        setHasSketch(hasAnyFeature);
        isFirstPrompt.current = !hasAnyFeature;
      }
    }
    setLoading(false);
  };

  const handleRefinementChange = (newState: RefinementState) => {
    setAllRefinements(prev => {
      const updated = { ...prev, [activeLayer]: newState };
      syncToDatabase({ allRefinements: updated });
      return updated;
    });
  };

  const handleConfirmSetup = () => {
    setPhase("editing");
    syncToDatabase({ phase: "editing" });
  };

  const handleGenerate = async (description: string) => {
    const newMessages: Message[] = [...messages, { sender: 'user', text: description }];
    setMessages(newMessages);
    const loadingToast = toast.loading("PROCESSING LINGUISTIC DESCRIPTION...");
    
    let backendPrompt = description;
    if (isFirstPrompt.current) {
      backendPrompt = `Suspect is a ${ageGroup} ${gender}. ` + description;
      isFirstPrompt.current = false;
    }

    await supabase.from('sessions').update({ raw_input: backendPrompt, status: 'Processing' }).eq('id', sessionId);

    try {
      const response = await fetch(`${API_BASE_URL}/mistral-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: backendPrompt, sessionId, conversation: newMessages }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.text || "Connection Fault");

      toast.dismiss(loadingToast);
      if (data.text) setMessages(prev => [...prev, { sender: 'bot', text: data.text }]);

      const updates: any = {};

      if (data.generated_images && data.generated_images.length > 0) {
        data.generated_images.forEach((imgObj: { category: string, image: string }) => {
          const formattedImage = `data:image/png;base64,${imgObj.image}`;
          if (imgObj.category === 'eyes') { setEyeImage(formattedImage); updates.eyeImage = formattedImage; }
          else if (imgObj.category === 'mouth') { setMouthImage(formattedImage); updates.mouthImage = formattedImage; }
          else if (imgObj.category === 'nose') { setNoseImage(formattedImage); updates.noseImage = formattedImage; }
          else if (imgObj.category === 'hair') { setHairImage(formattedImage); updates.hairImage = formattedImage; }
        });

        setHasSketch(true);
        toast.success("DATABASE ATTRIBUTES RENDERED.");
        const detected = data.generated_images.map((g: any) => g.category).find((c: string) => ['eyes','nose','mouth','hair'].includes(c));
        if (detected) setActiveLayer(detected as ComponentLayer);
      }

      await supabase.from('sessions').update({ status: 'In Progress' }).eq('id', sessionId);
      await syncToDatabase(updates);
      return data.text; 

    } catch (error) {
      console.error("Backend Error:", error);
      toast.dismiss(loadingToast);
      toast.error("NETWORK ERROR: BACKEND UNREACHABLE.");
      await supabase.from('sessions').update({ status: 'Error' }).eq('id', sessionId);
    }
  };

  const handleFinalizeSketch = async () => {
    setIsProcessing(true);
    const loadingToast = toast.loading("EXECUTING MATHEMATICAL FEATURE FUSION...");
    try {
      const response = await fetch(`${API_BASE_URL}/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          faceShape,
          features: { eyes: eyeImage, nose: noseImage, mouth: mouthImage, hair: hairImage },
          refinements: allRefinements
        }),
      });

      const data = await response.json();
      if (!response.ok || data.status === "error") throw new Error(data.message || "Fusion Failed");

      if (finalBlendedImage) setHistory(prev => [...prev, { image: finalBlendedImage, timestamp: Date.now() }]);
      setRedoStack([]);
      setFinalBlendedImage(data.blended_image);
      setPhase("blended");
      
      await syncToDatabase({ finalBlendedImage: data.blended_image, phase: "blended" });
      
      toast.dismiss(loadingToast);
      toast.success("FUSION COMPLETE.");
    } catch (error) {
      toast.dismiss(loadingToast);
      toast.error("FUSION ERROR: FAILED TO BLEND COMPOSITE.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleEnhanceSketch = async () => {
    if (!finalBlendedImage) return;
    setIsProcessing(true);
    setProcessingProgress(0);
    const loadingToast = toast.loading("APPLYING NEURAL SHADING ALGORITHM...");
    
    const progressInterval = setInterval(() => {
      setProcessingProgress(prev => {
        const next = prev + Math.random() * 30;
        return next >= 90 ? 90 : next;
      });
    }, 500);
    
    try {
      const response = await fetch(`${API_BASE_URL}/enhance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: finalBlendedImage }),
      });

      const data = await response.json();
      if (!response.ok || data.status === "error") throw new Error(data.message || "Enhancement Failed");

      setHistory(prev => [...prev, { image: finalBlendedImage, timestamp: Date.now() }]);
      setRedoStack([]);
      setFinalBlendedImage(data.enhanced_image);
      setPhase("enhanced");

      await syncToDatabase({ finalBlendedImage: data.enhanced_image, phase: "enhanced" });

      toast.dismiss(loadingToast);
      toast.success("NEURAL SHADING COMPLETE.");
    } catch (error) {
      toast.dismiss(loadingToast);
      toast.error("ENHANCEMENT ERROR.");
    } finally {
      clearInterval(progressInterval);
      setProcessingProgress(100);
      setTimeout(() => setProcessingProgress(0), 1000);
      setIsProcessing(false);
    }
  };

  const handleValidateSketch = async () => {
    if (!finalBlendedImage) return;
    setIsProcessing(true);
    const loadingToast = toast.loading("CROSS-REFERENCING DATABASE RECORDS...");
    try {
      const response = await fetch(`${API_BASE_URL}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: finalBlendedImage }),
      });
      
      const data = await response.json();
      if (!response.ok || data.status === "error") throw new Error(data.message || "Validation failed");
      
      setValidationResult(data);
      setPhase("validated");

      await syncToDatabase({ phase: "validated" });

      toast.dismiss(loadingToast);
      toast.success(`MATCH ACQUIRED: ${data.confidence}% CONFIDENCE.`);
      
      if (sessionId && data.match) {
        await addSessionLog(sessionId, 'validation', `Verification - Match: ${data.match}, Similarity: ${data.confidence}%`);
      }
    } catch (error) {
      toast.dismiss(loadingToast);
      toast.error("VALIDATION ERROR: DATABASE UNREACHABLE.");
    } finally {
      setIsProcessing(false);
    }
  };

  // --- NEW PDF EXPORT LOGIC (Now safely executes strictly when finalBlendedImage exists) ---
  const handleExport = async () => {
    if (!finalBlendedImage) {
      toast.error("PROTOCOL VIOLATION: NO IMAGE TO EXPORT.");
      return;
    }

    const toastId = toast.loading("GENERATING CONFIDENTIAL DOSSIER...");

    try {
      let agentName = "Authorized Agent";
      if (user?.id) {
        const { data: profile } = await supabase.from('profiles').select('full_name').eq('id', user.id).single();
        if (profile?.full_name) agentName = profile.full_name;
      }

      const doc = new jsPDF({ unit: 'pt', format: 'a4' });
      const pageW = doc.internal.pageSize.getWidth();
      const margin = 40;
      let y = 50;

      // HEADER
      doc.setFont("helvetica", "bold");
      doc.setFontSize(22);
      doc.setTextColor(20, 20, 20);
      doc.text("OFFICIAL FORENSIC DOSSIER", pageW / 2, y, { align: 'center' });
      y += 20;
      
      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(100, 100, 100);
      doc.text("RESTRICTED ACCESS - LAW ENFORCEMENT ONLY", pageW / 2, y, { align: 'center' });
      y += 40;

      // METADATA PANEL
      doc.setFontSize(10);
      doc.setTextColor(0, 0, 0);
      doc.setFont("helvetica", "bold");
      doc.text("CASE LOG IDENTIFIER:", margin, y);
      doc.setFont("helvetica", "normal");
      doc.text(sessionId || "UNKNOWN", margin + 140, y);
      y += 15;

      doc.setFont("helvetica", "bold");
      doc.text("GENERATION TIMESTAMP:", margin, y);
      doc.setFont("helvetica", "normal");
      doc.text(new Date().toLocaleString(), margin + 140, y);
      y += 15;

      doc.setFont("helvetica", "bold");
      doc.text("INVESTIGATING AGENT:", margin, y);
      doc.setFont("helvetica", "normal");
      doc.text(agentName.toUpperCase(), margin + 140, y);
      y += 35;

      // SUBJECT DATA
      doc.setFillColor(240, 240, 240);
      doc.rect(margin, y, pageW - margin * 2, 80, 'F');
      y += 20;
      doc.setFontSize(12);
      doc.setFont("helvetica", "bold");
      doc.text("SUBJECT DEMOGRAPHICS", margin + 15, y);
      y += 20;
      
      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      doc.text(`REFERENCE ALIAS: ${suspectName ? suspectName.toUpperCase() : 'UNKNOWN SUBJECT'}`, margin + 15, y);
      y += 15;
      doc.text(`BIOLOGICAL SEX: ${gender ? gender.toUpperCase() : 'UNSPECIFIED'}`, margin + 15, y);
      doc.text(`ESTIMATED AGE: ${ageGroup ? ageGroup.toUpperCase() : 'UNSPECIFIED'}`, margin + 200, y);
      y += 50;

      // IMAGE RENDER
      const imgWidth = 300;
      const imgHeight = 300;
      const imgX = (pageW - imgWidth) / 2;
      
      doc.setDrawColor(0);
      doc.setLineWidth(1);
      doc.rect(imgX - 2, y - 2, imgWidth + 4, imgHeight + 4);
      doc.addImage(finalBlendedImage, 'PNG', imgX, y, imgWidth, imgHeight);
      y += imgHeight + 40;

      // NARRATIVE
      if (messages && messages.length > 0) {
        doc.setFontSize(12);
        doc.setFont("helvetica", "bold");
        doc.text("WITNESS NARRATIVE PROTOCOL", margin, y);
        y += 20;
        
        doc.setFontSize(9);
        doc.setFont("helvetica", "normal");
        
        for (const m of messages) {
          if (m.sender === 'user') {
            const lines = doc.splitTextToSize(`DIRECTIVE: ${m.text}`, pageW - margin * 2);
            if (y + lines.length * 12 > doc.internal.pageSize.getHeight() - margin) {
              doc.addPage();
              y = margin + 20;
            }
            doc.text(lines, margin, y);
            y += lines.length * 12 + 8;
          }
        }
      }

      const filename = `DOSSIER_${sessionId?.slice(0,8) || 'EXPORT'}.pdf`;
      doc.save(filename);

      toast.dismiss(toastId);
      toast.success('DOSSIER EXPORTED SECURELY.');
      if (sessionId) await addSessionLog(sessionId, 'export', `Generated Official PDF Dossier.`);
    } catch (e) {
      console.error(e);
      toast.dismiss(toastId);
      toast.error('CRITICAL: PDF GENERATION FAILED.');
    }
  };

  const renderHeader = () => (
    <header className="border-b border-border bg-card/80 backdrop-blur-md shrink-0 z-50">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="outline" size="sm" onClick={() => navigate('/dashboard')} className="font-mono text-xs uppercase tracking-wider h-8">
              [ RETURN ]
            </Button>
            <div>
              <h1 className="text-sm md:text-base font-bold uppercase tracking-wider leading-tight">Forensic Workspace</h1>
              <p className="text-[10px] text-muted-foreground font-mono leading-tight mt-0.5">CASE ID: {sessionId?.slice(0, 12)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleUndo} disabled={history.length === 0} className="font-mono text-[10px] md:text-xs h-8">
              [ UNDO ]
            </Button>
            <Button variant="ghost" size="sm" onClick={handleRedo} disabled={redoStack.length === 0} className="font-mono text-[10px] md:text-xs h-8">
              [ REDO ]
            </Button>
            <div className="hidden md:block text-[10px] font-mono font-bold text-muted-foreground bg-secondary px-2 py-1.5 rounded uppercase tracking-wider border border-border">
              STATUS: {session?.status || 'ACTIVE'}
            </div>
          </div>
        </div>
      </div>
    </header>
  );

  if (authLoading || (loading && !session)) {
    return (
      <div className="h-screen w-full bg-background flex flex-col items-center justify-center space-y-4 overflow-hidden">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">ACCESSING FORENSIC RECORDS...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-full bg-background font-sans overflow-hidden selection:bg-primary/30">
      {renderHeader()}

      <main className="flex-1 min-h-0 container mx-auto px-2 md:px-4 py-4 lg:overflow-hidden overflow-y-auto flex flex-col">
        
        {phase === "setup" && (
          <div className="flex-1 w-full max-w-4xl mx-auto flex flex-col justify-center items-center space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-xl font-bold uppercase tracking-widest pb-2">SUBJECT INITIALIZATION</h2>
              <p className="text-muted-foreground text-xs">DEFINE BASELINE MORPHOLOGICAL TRAITS BEFORE FEATURE GENERATION.</p>
            </div>
            
            <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-6 bg-card border border-border p-6 rounded-lg shadow-sm">
              <div className="space-y-6">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">SUBJECT REFERENCE NAME (OPTIONAL)</label>
                  <input
                    className="w-full px-3 py-2 text-sm rounded bg-background border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all font-mono"
                    placeholder="UNKNOWN_SUBJECT_01"
                    value={suspectName}
                    onChange={(e) => setSuspectName(e.target.value)}
                  />
                </div>
                
                <div className="space-y-3">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest block">CRANIAL STRUCTURE</label>
                  <div className="flex gap-2">
                    {["oval", "round", "square"].map((shape) => (
                      <div 
                        key={shape}
                        onClick={() => setFaceShape(shape)}
                        className={`cursor-pointer border-2 p-2 flex-1 transition-all flex flex-col items-center gap-2 bg-background hover:bg-secondary/50 rounded-sm ${
                          faceShape === shape ? "border-primary shadow-sm" : "border-border"
                        }`}
                      >
                        <img src={`/faces/${shape}_face.png`} alt={shape} className="w-10 h-10 object-contain opacity-80" />
                        <p className="text-center font-bold uppercase text-[10px] tracking-wider">{shape}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <div className="space-y-3">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest block">BIOLOGICAL SEX</label>
                  <div className="flex gap-2">
                    {["male", "female"].map(g => (
                      <Button 
                        key={g} 
                        variant={gender === g ? "default" : "outline"} 
                        onClick={() => setGender(g)} 
                        className="flex-1 uppercase text-xs font-bold tracking-wider rounded-sm h-10"
                      >
                        {g}
                      </Button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest block">ESTIMATED AGE</label>
                  <div className="flex flex-col gap-2">
                    {["young", "middle-aged", "old"].map(a => (
                      <Button 
                        key={a} 
                        variant={ageGroup === a ? "default" : "outline"} 
                        onClick={() => setAgeGroup(a)} 
                        className="w-full uppercase text-xs font-bold tracking-wider rounded-sm h-10"
                      >
                        {a === "middle-aged" ? "MIDDLE-AGED" : a}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <Button 
              size="default"
              onClick={handleConfirmSetup}
              className="w-full max-w-sm h-12 text-xs font-bold tracking-widest uppercase rounded-sm shadow-md"
            >
              CONFIRM PARAMETERS & INITIALIZE
            </Button>
          </div>
        )}

        {phase === "editing" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full min-h-0">
            <div className="lg:col-span-3 h-full min-h-0 flex flex-col border border-border rounded-lg bg-card shadow-sm overflow-hidden">
              <InputPanel onGenerate={handleGenerate} initialValue={session?.raw_input || ''} />
            </div>
            
            <div className="lg:col-span-6 h-full min-h-0 flex flex-col border border-border rounded-lg bg-card shadow-sm p-2 overflow-hidden">
               <div className="flex-1 min-h-0">
                  <CanvasPanel 
                    caseId={sessionId?.slice(0, 13) || ''}
                    realismScore={85}
                    hasSketch={hasSketch}
                    faceShape={faceShape}
                    eyeImage={eyeImage} 
                    mouthImage={mouthImage}
                    noseImage={noseImage}
                    hairImage={hairImage} 
                    allRefinements={allRefinements}
                  />
               </div>
               {hasSketch && (
                 <div className="shrink-0 pt-3 pb-1 px-1 space-y-2 border-t border-border mt-2">
                   {!interviewActive ? (
                     <Button 
                       className="w-full h-10 text-xs font-bold uppercase tracking-widest rounded-sm" 
                       onClick={handleFinalizeSketch}
                       disabled={isProcessing}
                     >
                       {isProcessing ? "PROCESSING FUSION..." : "EXECUTE BLEND PROTOCOL"}
                     </Button>
                   ) : (
                     <div className="space-y-2">
                       <div className="bg-secondary p-2 border border-border flex flex-col justify-center">
                         <p className="text-[10px] font-mono font-bold text-primary mb-1.5 uppercase">
                           STAGE {interviewStage + 1}/4: {INTERVIEW_FLOW[interviewStage]}
                         </p>
                         <Progress value={((interviewStage + 1) / 4) * 100} className="h-1 rounded-none" />
                       </div>
                       <Button 
                         className="w-full h-10 text-[10px] md:text-xs font-bold uppercase tracking-widest rounded-sm" 
                         onClick={handleConfirmNext}
                       >
                         {interviewStage === 3 ? "FINALIZE INTERVIEW" : `CONFIRM & PROCEED: [ ${INTERVIEW_FLOW[Math.min(interviewStage + 1, 3)].toUpperCase()} ]`}
                       </Button>
                     </div>
                   )}
                   {!interviewActive && hasSketch && (
                     <Button 
                       variant="outline"
                       className="w-full h-8 uppercase text-[10px] tracking-widest font-bold rounded-sm border-dashed" 
                       onClick={handleStartInterview}
                     >
                       INITIATE STRUCTURED INTERVIEW
                     </Button>
                   )}
                 </div>
               )}
            </div>
            
            <div className="lg:col-span-3 h-full min-h-0 flex flex-col border-2 border-border bg-card rounded-lg shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-primary z-10" />
              <RefinementPanel 
                selectedLayer={activeLayer}
                onLayerChange={setActiveLayer}
                refinement={allRefinements[activeLayer]} 
                onRefinementChange={handleRefinementChange}
              />
            </div>
          </div>
        )}

        {(phase === "blended" || phase === "enhanced" || phase === "validated") && finalBlendedImage && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full min-h-0">
            <div className="lg:col-span-8 h-full min-h-0 flex flex-col border border-border bg-card p-4 rounded-lg shadow-sm">
              <div className="flex justify-between items-center mb-4 border-b border-border pb-3 shrink-0">
                 <h3 className="text-sm md:text-base font-bold uppercase tracking-widest text-primary">OFFICIAL COMPOSITE RECORD</h3>
                 <span className="text-[10px] font-mono bg-secondary px-2 py-1 border border-border">CONFIDENTIAL</span>
              </div>
              <div className="flex-1 min-h-0 bg-secondary/20 border border-border rounded flex items-center justify-center p-4 relative overflow-hidden">
                <div className="absolute top-4 left-4 w-4 h-4 border-t-2 border-l-2 border-primary/50" />
                <div className="absolute top-4 right-4 w-4 h-4 border-t-2 border-r-2 border-primary/50" />
                <div className="absolute bottom-4 left-4 w-4 h-4 border-b-2 border-l-2 border-primary/50" />
                <div className="absolute bottom-4 right-4 w-4 h-4 border-b-2 border-r-2 border-primary/50" />
                <img 
                  src={finalBlendedImage} 
                  alt="Final Blended Sketch" 
                  className="w-full h-full object-contain filter contrast-125" 
                />
              </div>
            </div>

            <div className="lg:col-span-4 h-full min-h-0 flex flex-col gap-4">
              <div className="border border-border bg-card p-4 rounded-lg shadow-sm shrink-0">
                <h4 className="font-bold text-[10px] uppercase tracking-widest text-muted-foreground mb-3 pb-2 border-b border-border">CURRENT STATUS PROTOCOL</h4>
                
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                    <p className="text-[10px] font-mono font-bold text-primary uppercase">FEATURE FUSION ACTIVE</p>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <div className={`w-1.5 h-1.5 rounded-full ${(phase === "enhanced" || phase === "validated") ? "bg-primary" : "bg-muted"}`} />
                    <p className={`text-[10px] font-mono font-bold uppercase ${(phase === "enhanced" || phase === "validated") ? "text-primary" : "text-muted-foreground"}`}>NEURAL ENHANCEMENTS APPLIED</p>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className={`w-1.5 h-1.5 rounded-full ${phase === "validated" ? "bg-primary" : "bg-muted"}`} />
                    <p className={`text-[10px] font-mono font-bold uppercase ${phase === "validated" ? "text-primary" : "text-muted-foreground"}`}>IDENTITY CROSS-REFERENCED</p>
                  </div>
                </div>

                {isProcessing && processingProgress > 0 && (
                  <div className="mt-4 space-y-1.5 border border-border p-2 rounded-sm bg-secondary/50">
                    <div className="flex justify-between text-[8px] uppercase font-bold text-primary tracking-widest">
                      <span>SYSTEM PROCESSING</span>
                      <span className="font-mono">{Math.round(processingProgress)}%</span>
                    </div>
                    <Progress value={processingProgress} className="h-1 rounded-none bg-border" />
                  </div>
                )}
              </div>

              <div className="flex-1 min-h-0 border border-border bg-card p-4 rounded-lg shadow-sm flex flex-col">
                <h4 className="font-bold text-[10px] uppercase tracking-widest text-muted-foreground mb-3 pb-2 border-b border-border shrink-0">NEXT AUTHORIZED ACTIONS</h4>
                
                <div className="flex flex-col gap-3 flex-1">
                  {phase === "blended" && (
                    <Button 
                      className="w-full h-12 text-xs font-bold tracking-widest uppercase rounded-sm shrink-0" 
                      onClick={handleEnhanceSketch} 
                      disabled={isProcessing}
                    >
                      EXECUTE NEURAL SHADING
                    </Button>
                  )}

                  {(phase === "enhanced" || phase === "validated") && (
                    <Button 
                      className={`w-full h-12 text-xs font-bold tracking-widest uppercase rounded-sm shrink-0 border ${phase === "validated" ? "bg-secondary text-primary" : ""}`} 
                      onClick={handleValidateSketch} 
                      disabled={isProcessing || phase === "validated"}
                    >
                      EXECUTE DATABASE VALIDATION
                    </Button>
                  )}

                  <Button 
                    variant="secondary"
                    className="w-full h-12 text-xs font-bold tracking-widest uppercase rounded-sm shrink-0 border border-primary/20 text-primary hover:bg-primary/10" 
                    onClick={handleExport}
                    disabled={isProcessing}
                  >
                    EXPORT OFFICIAL DOSSIER
                  </Button>

                  <Button variant="outline" className="w-full h-10 font-bold uppercase text-[10px] tracking-widest rounded-sm shrink-0 mt-auto" onClick={() => { setFinalBlendedImage(null); setPhase("editing"); }}>
                    ABORT PROTOCOL / RETURN TO EDITING
                  </Button>
                </div>

                {validationResult && (
                  <div className="mt-4 border-t border-border pt-4 shrink-0">
                    <div className="border border-primary bg-primary/5 p-3 rounded-sm space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest">TARGET MATCH FOUND</span>
                        <span className="text-xs font-bold font-mono text-primary">{validationResult.match}</span>
                      </div>
                      <div className="space-y-1">
                        <div className="flex justify-between items-center text-[9px] font-bold text-muted-foreground uppercase tracking-widest">
                          <span>SIMILARITY INDEX</span>
                          <span className="font-mono">{validationResult.confidence}%</span>
                        </div>
                        <Progress value={validationResult.confidence} className="h-1.5 bg-border rounded-none" />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Index;