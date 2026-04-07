"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { type ChatMessage, type ResearchQuery } from "@/lib/types"
import { type Source } from "@/lib/types"
import { ChatMessageBubble } from "@/components/chat-message"
import { ChatInput } from "@/components/chat-input"
import { ThinkingSkeleton } from "@/components/thinking-skeleton"
import { ResearchSidebar } from "@/components/research-sidebar"
import { WelcomeScreen } from "@/components/welcome-screen"
import { Button } from "@/components/ui/button"
import { Brain, PanelLeft, Sparkles } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export default function Page() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState("")
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeQueryId, setActiveQueryId] = useState<string | undefined>()
  const scrollRef = useRef<HTMLDivElement>(null)

  const [recentQueries] = useState<ResearchQuery[]>([
    {
      id: "1",
      title: "CRISPR gene therapy advances for SCD",
      timestamp: new Date(Date.now() - 1000 * 60 * 30),
      messageCount: 4,
    },
    {
      id: "2",
      title: "GLP-1 receptor agonists mechanism",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 3),
      messageCount: 6,
    },
    {
      id: "3",
      title: "Gut microbiome and neurodegeneration",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 28),
      messageCount: 3,
    },
    {
      id: "4",
      title: "Immunotherapy for pancreatic cancer",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 72),
      messageCount: 5,
    },
    {
      id: "5",
      title: "mRNA vaccine platform developments",
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 120),
      messageCount: 8,
    },
  ])

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, scrollToBottom])

  async function callBackend(query: string) {
    try {
      setIsLoading(true)

      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 600000)

      const response = await fetch("http://localhost:8000/generate-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)
      const data = await response.json()

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer,
        // sources now come straight from the backend as a structured array
        sources: (data.sources ?? []) as Source[],
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Error connecting to backend:", error)

      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "⚠️ Error connecting to RAG backend. Make sure FastAPI server is running on port 8000.",
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  function handleSubmit() {
    if (!inputValue.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    const query = inputValue.trim()
    setInputValue("")
    callBackend(query)
  }

  function handleStop() {
    setIsLoading(false)
  }

  function handleNewChat() {
    setMessages([])
    setActiveQueryId(undefined)
    setInputValue("")
  }

  function handleSelectQuery(id: string) {
    setActiveQueryId(id)
    setMessages([])
  }

  function handleSuggestionClick(text: string) {
    setInputValue(text)

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    }

    setMessages([userMessage])
    callBackend(text)
  }

  const hasMessages = messages.length > 0

  return (
    <TooltipProvider>
      <div className="flex h-dvh flex-col bg-background">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-border/50 bg-card/50 backdrop-blur-sm px-4 py-3">
          <div className="flex items-center gap-3">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9 rounded-xl text-muted-foreground hover:text-foreground"
                  onClick={() => setSidebarOpen(true)}
                >
                  <PanelLeft className="h-4 w-4" />
                  <span className="sr-only">Toggle sidebar</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Recent Research</TooltipContent>
            </Tooltip>

            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                <Brain className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h1 className="text-sm font-semibold text-foreground leading-tight">
                  BioResearch AI
                </h1>
                <p className="text-xs text-muted-foreground leading-tight">
                  Biomedical Research Assistant
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5 rounded-xl text-muted-foreground hover:text-foreground"
                  onClick={handleNewChat}
                >
                  <Sparkles className="h-4 w-4" />
                  <span className="hidden sm:inline text-xs">New Chat</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Start new research query</TooltipContent>
            </Tooltip>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-hidden">
          {hasMessages ? (
            <div ref={scrollRef} className="h-full overflow-y-auto">
              <div className="mx-auto max-w-3xl px-4 py-6 space-y-6">
                {messages.map((message) => (
                  <ChatMessageBubble key={message.id} message={message} />
                ))}
                {isLoading && <ThinkingSkeleton />}
                <div className="h-4" />
              </div>
            </div>
          ) : (
            <div className="h-full overflow-y-auto">
              <div className="mx-auto max-w-3xl">
                <WelcomeScreen onSuggestionClick={handleSuggestionClick} />
              </div>
            </div>
          )}
        </div>

        {/* Uploaded files indicator */}
        {uploadedFiles.length > 0 && (
          <div className="text-xs text-muted-foreground px-4 pb-1">
            {uploadedFiles.map((file, index) => (
              <div key={index}>📄 {file.name}</div>
            ))}
          </div>
        )}

        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          onStop={handleStop}
          isLoading={isLoading}
          onFileUpload={(files) => setUploadedFiles(files)}
        />

        <ResearchSidebar
          open={sidebarOpen}
          onOpenChange={setSidebarOpen}
          queries={recentQueries}
          activeQueryId={activeQueryId}
          onSelectQuery={handleSelectQuery}
          onNewChat={handleNewChat}
        />
      </div>

      <input
        type="file"
        accept=".pdf"
        hidden
        id="pdfUpload"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            setUploadedFiles(Array.from(e.target.files))
          }
        }}
      />
    </TooltipProvider>
  )
}
              
  