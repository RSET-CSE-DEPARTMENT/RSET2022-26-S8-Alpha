import { useState, useRef, useEffect } from "react";
import { useReactMediaRecorder } from "react-media-recorder";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { useParams } from "react-router-dom";

// --- CONFIGURATION ---
const API_BASE_URL = import.meta.env.DEV 
  ? "http://127.0.0.1:7860" 
  : "https://arunvjo04-smart-forensic-backend.hf.space";

interface Message {
  sender: "user" | "bot";
  text: string;
}

interface InputPanelProps {
  onGenerate: (description: string) => Promise<string | void | any>; 
  initialValue: string;
}

type UIState = "TEXT_INPUT" | "CONFIRM_YES_NO" | "REGEN_OR_NEW";

export const InputPanel = ({ onGenerate, initialValue }: InputPanelProps) => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const CHAT_HISTORY_KEY = sessionId ? `forensic-chat-history-${sessionId}` : "";

  const STARTER_BOT: Message = {
    sender: "bot",
    text: "SYSTEM READY. DEMOGRAPHIC BASELINE ESTABLISHED. COMMENCING FEATURE GENERATION. DESCRIBE THE OCULAR REGION (EYES).",
  };

  // --- STATE ---
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window === "undefined" || !sessionId) return [STARTER_BOT];
    try {
      const saved = window.localStorage.getItem(CHAT_HISTORY_KEY);
      return saved ? JSON.parse(saved) : [STARTER_BOT];
    } catch (e) {
      console.error("Failed to parse chat history:", e);
      return [STARTER_BOT];
    }
  });

  const [inputValue, setInputValue] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [uiState, setUiState] = useState<UIState>("TEXT_INPUT");
  const scrollRef = useRef<HTMLDivElement>(null);

  // --- SMART UI STATE PARSER ---
  // Automatically detects what buttons to show based on the bot's text response
  const determineUiState = (botText: string): UIState => {
    const upperText = botText.toUpperCase();
    if (upperText.includes("(YES/NO)")) return "CONFIRM_YES_NO";
    if (upperText.includes("[REGENERATE]") || upperText.includes("[NEW]")) return "REGEN_OR_NEW";
    return "TEXT_INPUT";
  };

  // --- HANDLERS ---
  const editMessageAt = (index: number) => {
    const msg = messages[index];
    if (!msg || msg.sender !== "user") return;
    setMessages((prev) => prev.slice(0, index));
    setInputValue(msg.text);
    setUiState("TEXT_INPUT"); // Reset UI state on edit
  };

  const clearChat = () => {
    setMessages([STARTER_BOT]);
    setUiState("TEXT_INPUT");
    if (typeof window !== "undefined" && sessionId) {
      window.localStorage.removeItem(CHAT_HISTORY_KEY);
    }
    toast.success("AUDIT LOG CLEARED.");
  };

  // --- AUDIO LOGIC ---
  const handleSendAudio = async (blobUrl: string) => {
    if (!sessionId) {
      toast.error("SYSTEM FAULT: SESSION ID MISSING.");
      return;
    }
    setIsLoading(true);
    setMessages((prev) => [...prev, { sender: "user", text: "[ PROCESSING AUDIO FEED... ]" }]);
    
    try {
      const audioBlob = await fetch(blobUrl).then((res) => res.blob());
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.wav");
      formData.append("sessionId", sessionId);

      const voiceResponse = await fetch(`${API_BASE_URL}/voice`, { method: "POST", body: formData });
      if (!voiceResponse.ok) throw new Error("Audio processing failed");
      
      const voiceData = await voiceResponse.json();
      
      if (voiceData.transcript) {
        setMessages((prev) => [
          ...prev.slice(0, -1),
          { sender: "user", text: `[VOICE TRANSCRIPT]: ${voiceData.transcript}` },
        ]);
        
        const backendReply = await onGenerate(voiceData.transcript);
        const botResponseText = typeof backendReply === "string" && backendReply.trim() !== ""
          ? backendReply
          : "DIRECTIVE PROCESSED. SKETCH UPDATED.";

        setUiState(determineUiState(botResponseText));
        setMessages((prev) => [...prev, { sender: "bot", text: botResponseText }]);
      } else {
        throw new Error("No transcript returned");
      }
    } catch (error) {
      toast.error("AUDIO SERVICE UNAVAILABLE.");
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { sender: "bot", text: "AUDIO PROCESSING FAILED. REVERT TO MANUAL TEXT INPUT." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const { status, startRecording, stopRecording } = useReactMediaRecorder({
    audio: true,
    onStop: handleSendAudio,
  });

  // --- TEXT LOGIC ---
  const handleSendMessage = async (textOverride?: string) => {
    const textToSend = typeof textOverride === "string" ? textOverride : inputValue.trim();
    if (!sessionId || !textToSend || isLoading || status === "recording") return;

    setMessages((prev) => [...prev, { sender: "user", text: textToSend }]);
    if (typeof textOverride !== "string") setInputValue("");
    
    // Temporarily hide buttons while processing
    setUiState("TEXT_INPUT"); 
    setIsLoading(true);

    try {
      const backendReply = await onGenerate(textToSend);
      
      const botResponseText = typeof backendReply === "string" && backendReply.trim() !== ""
        ? backendReply
        : "DIRECTIVE PROCESSED. RENDER UPDATED.";

      setUiState(determineUiState(botResponseText));
      setMessages((prev) => [...prev, { sender: "bot", text: botResponseText }]);
    } catch (error) {
      toast.error("CONNECTION SEVERED.");
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "SYSTEM ERROR: NEURAL ENGINE UNREACHABLE." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- EFFECTS ---
  useEffect(() => {
    if (typeof window !== "undefined" && sessionId) {
      window.localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(messages));
    }
    // Check latest bot message to maintain UI state on reload
    if (messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.sender === "bot") setUiState(determineUiState(lastMsg.text));
    }
  }, [messages, CHAT_HISTORY_KEY, sessionId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, uiState]);

  if (!sessionId) {
    return (
      <div className="flex flex-col h-full bg-card p-3 shadow-inner overflow-hidden border border-border rounded-sm items-center justify-center">
        <p className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground animate-pulse">INITIALIZING FEED...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-card p-3 shadow-inner overflow-hidden border border-border rounded-sm">
      
      {/* HEADER SECTION */}
      <div className="flex items-center justify-between border-b border-border pb-2 shrink-0">
        <h2 className="text-xs font-bold uppercase tracking-widest text-primary">NLP Terminal</h2>
        <Button
          variant="outline"
          size="sm"
          className="h-6 text-[9px] font-mono tracking-widest rounded-sm px-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
          onClick={clearChat}
        >
          [ CLEAR ]
        </Button>
      </div>

      {/* CHAT LOG AREA (INTERNAL SCROLL ONLY) */}
      <div 
        className="flex-1 min-h-0 overflow-y-auto my-2 pr-2 space-y-3 custom-scrollbar"
        ref={scrollRef}
      >
        {messages.map((msg, index) => {
          const isUser = msg.sender === "user";
          return (
            <div
              key={index}
              className={`flex flex-col p-2 rounded-sm border ${
                isUser 
                  ? "bg-primary/5 border-primary/20 ml-4" 
                  : "bg-secondary/20 border-border mr-4"
              }`}
            >
              <div className="flex justify-between items-start mb-1">
                <span className={`text-[8px] font-bold tracking-widest uppercase ${isUser ? "text-primary" : "text-muted-foreground"}`}>
                  {isUser ? "AGENT DIRECTIVE" : "SYSTEM RESPONSE"}
                </span>
                
                {isUser && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-4 px-1 text-[8px] font-mono text-muted-foreground hover:text-primary"
                    onClick={() => editMessageAt(index)}
                  >
                    [ EDIT ]
                  </Button>
                )}
              </div>
              <p className="text-[10px] font-mono leading-relaxed uppercase text-foreground/90 whitespace-pre-wrap">
                {msg.text}
              </p>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex flex-col p-2 rounded-sm border bg-secondary/20 border-border mr-4">
             <span className="text-[8px] font-bold tracking-widest uppercase text-muted-foreground mb-1">SYSTEM RESPONSE</span>
             <p className="text-[10px] font-mono uppercase text-primary animate-pulse">
               PROCESSING DIRECTIVE...
             </p>
          </div>
        )}
      </div>

      {/* QUICK ACTION / NLP DECISION AREA */}
      <div className="shrink-0 pt-2 border-t border-border flex flex-col gap-2">
        
        {/* State 1: Confirmation Buttons */}
        {uiState === "CONFIRM_YES_NO" && (
          <div className="flex gap-2 w-full">
            <Button 
              onClick={() => handleSendMessage("YES")} 
              className="flex-1 bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border border-emerald-500/30 text-[10px] font-bold tracking-widest h-8 rounded-sm"
            >
              [ CONFIRM RENDER ]
            </Button>
            <Button 
              onClick={() => handleSendMessage("NO")} 
              className="flex-1 bg-destructive/10 text-destructive hover:bg-destructive/20 border border-destructive/30 text-[10px] font-bold tracking-widest h-8 rounded-sm"
            >
              [ REJECT RENDER ]
            </Button>
          </div>
        )}

        {/* State 2: Regeneration Buttons */}
        {uiState === "REGEN_OR_NEW" && (
          <div className="flex gap-2 w-full">
            <Button 
              onClick={() => handleSendMessage("REGENERATE")} 
              className="flex-1 bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border border-amber-500/30 text-[9px] font-bold tracking-widest h-8 rounded-sm px-1"
            >
              [ REGENERATE RENDER ]
            </Button>
            <Button 
              onClick={() => handleSendMessage("NEW")} 
              className="flex-1 bg-primary/10 text-primary hover:bg-primary/20 border border-primary/30 text-[9px] font-bold tracking-widest h-8 rounded-sm px-1"
            >
              [ NEW PARAMETERS ]
            </Button>
          </div>
        )}

        {/* Standard Text Input */}
        <div className="flex gap-2 w-full">
          <Input
            placeholder={initialValue || "ENTER DIRECTIVE..."}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !isLoading && status !== "recording" && handleSendMessage()}
            disabled={isLoading || status === "recording"}
            className="flex-1 h-8 text-[10px] font-mono uppercase rounded-sm bg-background border-border placeholder:text-muted-foreground/50"
          />
          <Button
            onClick={status === "recording" ? stopRecording : startRecording}
            disabled={isLoading}
            variant={status === "recording" ? "destructive" : "outline"}
            className={`h-8 px-3 text-[9px] font-bold tracking-widest uppercase rounded-sm ${status === "recording" ? "animate-pulse" : ""}`}
          >
            {status === "recording" ? "[ STOP ]" : "[ REC ]"}
          </Button>
          <Button
            onClick={() => handleSendMessage()}
            disabled={isLoading || status === "recording" || !inputValue.trim()}
            className="h-8 px-3 text-[9px] font-bold tracking-widest uppercase rounded-sm"
          >
            [ SEND ]
          </Button>
        </div>

      </div>
    </div>
  );
};