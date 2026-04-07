import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Loader, ArrowRight, RefreshCw, FolderOpen } from 'lucide-react';
import { webgenService, QuestionField, DBConfig, GenerateResult } from '../services/webgenService';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  questionnaire?: QuestionField[];
}

interface AIChatProps {
  dbConfig: DBConfig | null;
  onWebsiteGenerated: (projectName: string, previewUrl: string, result?: GenerateResult) => void;
  onArtifactHtml?: (html: string) => void;
  onStreamEvent?: (type: string, data: Record<string, unknown>) => void;
  onOpenGallery?: () => void;
  loadedProject?: { name: string; previewUrl: string } | null;
}

type Phase = 'idle' | 'asking' | 'questionnaire' | 'generating' | 'done';

export default function AIChat({ dbConfig, onWebsiteGenerated, onArtifactHtml, onStreamEvent, onOpenGallery, loadedProject }: AIChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your AI design assistant. Describe the website you want to build and I\'ll generate it for you. Be as detailed as you like — include features, style preferences, pages, and content.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [phase, setPhase] = useState<Phase>('idle');
  const [currentIdea, setCurrentIdea] = useState('');
  const [questions, setQuestions] = useState<QuestionField[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [projectName, setProjectName] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // When a project is loaded from the gallery, switch to edit mode
  useEffect(() => {
    if (loadedProject && loadedProject.name) {
      setProjectName(loadedProject.name);
      setPhase('done');
      setMessages([{
        id: '1',
        role: 'assistant',
        content: 'Hello! I\'m your AI design assistant. Describe the website you want to build and I\'ll generate it for you. Be as detailed as you like — include features, style preferences, pages, and content.',
        timestamp: new Date(),
      }, {
        id: Date.now().toString(),
        role: 'assistant',
        content: `📂 Loaded "${loadedProject.name}" from your past projects. The preview is live on the right — describe any changes you'd like to make!`,
        timestamp: new Date(),
      }]);
    }
  }, [loadedProject]);

  const addMessage = (role: 'user' | 'assistant' | 'system', content: string, extra?: Partial<Message>) => {
    const msg: Message = {
      id: Date.now().toString() + Math.random(),
      role,
      content,
      timestamp: new Date(),
      ...extra,
    };
    setMessages(prev => [...prev, msg]);
    return msg;
  };

  // Step 1: User types idea → get questionnaire
  const handleSubmitIdea = async () => {
    if (!input.trim() || phase === 'asking' || phase === 'generating') return;

    const idea = input.trim();
    setCurrentIdea(idea);
    setInput('');
    addMessage('user', idea);
    setPhase('asking');

    addMessage('system', '🔍 Analyzing your idea and generating questions...');

    const result = await webgenService.getQuestionnaire(idea);

    if (!result.success || result.questions.length === 0) {
      addMessage('assistant', `I couldn't connect to the backend. ${result.error || 'Make sure the server is running on port 5000.'}`);
      setPhase('idle');
      return;
    }

    setQuestions(result.questions);
    // Set default answers
    const defaults: Record<string, string> = {};
    result.questions.forEach(q => {
      const qId = q.id || q.name || '';
      if (q.default) defaults[qId] = q.default;
      else if (q.options && q.options.length > 0) defaults[qId] = q.options[0];
      else defaults[qId] = '';
    });
    setAnswers(defaults);

    addMessage('assistant', `Great idea! I have ${result.questions.length} quick questions to help me build the perfect website. Fill them out below and click "Generate".`);
    setPhase('questionnaire');
  };

  // Step 2: User answers questionnaire → generate website (STREAMING)
  const handleGenerate = async () => {
    setPhase('generating');

    const answerParts = questions.map(q => {
      const qId = q.id || q.name || '';
      const val = answers[qId] || q.default || '';
      return `${q.label}: ${val}`;
    }).filter(Boolean);

    const fullPrompt = `${currentIdea}\n\nAdditional details:\n${answerParts.join('\n')}`;

    addMessage('user', 'Answers submitted — generate my website!');
    const progressMsgId = Date.now().toString();
    setMessages(prev => [...prev, {
      id: progressMsgId, role: 'system' as const,
      content: '🚀 Planning your website...',
      timestamp: new Date(),
    }]);

    let planData: GenerateResult['plan'] | undefined;
    let pagesDone = 0;

    try {
      await webgenService.generateWebsiteStream(
        fullPrompt,
        dbConfig || undefined,
        (type, data) => {
          // Forward every event to ArtifactPanel driver in parent
          onStreamEvent?.(type, data as Record<string, unknown>);

          if (type === 'plan') {
            planData = data.plan as GenerateResult['plan'];
            setMessages(prev => prev.map(m => m.id === progressMsgId
              ? { ...m, content: `🧠 Plan ready: ${(planData?.pages?.length ?? 0)} pages, building now...` }
              : m
            ));
          } else if (type === 'progress') {
            setMessages(prev => prev.map(m => m.id === progressMsgId
              ? { ...m, content: `⚡ ${data.message as string}` }
              : m
            ));
          } else if (type === 'artifact' && data.type === 'page') {
            pagesDone++;
            const html = data.content as string;
            // Show live preview for each completed page artifact
            if (onArtifactHtml) onArtifactHtml(html);
            setMessages(prev => prev.map(m => m.id === progressMsgId
              ? { ...m, content: `🎨 Built page "${data.name as string}" (${pagesDone}/${data.totalPages as number})...` }
              : m
            ));
          } else if (type === 'done') {
            const doneData = data as { plan: GenerateResult['plan']; previewUrl: string };
            const name = doneData.plan?.projectName || 'project';
            const previewUrl = doneData.previewUrl || webgenService.getPreviewUrl(name);
            setProjectName(name);
            setMessages(prev => prev.map(m => m.id === progressMsgId
              ? { ...m, role: 'system' as const, content: `✅ All ${doneData.plan?.pages?.length ?? 0} pages complete!` }
              : m
            ));
            addMessage('assistant', `✅ "${doneData.plan?.description || name}" is ready with ${doneData.plan?.pages?.length || 0} pages! Preview is live on the right. Use the chat to make edits.`);
            setPhase('done');
            onWebsiteGenerated(name, previewUrl, { success: true, plan: doneData.plan, previewUrl });
          } else if (type === 'error') {
            throw new Error(data.error as string);
          }
        }
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setMessages(prev => prev.map(m => m.id === progressMsgId
        ? { ...m, content: `❌ Generation failed: ${msg}` }
        : m
      ));
      addMessage('assistant', `❌ ${msg}. Please try again.`);
      setPhase('idle');
    }
  };

  // Step 3: Follow-up edits
  const handleEdit = async () => {
    if (!input.trim() || !projectName || phase === 'generating') return;

    const editPrompt = input.trim();
    setInput('');
    addMessage('user', editPrompt);
    setPhase('generating');
    addMessage('system', '✏️ Applying changes...');

    const result = await webgenService.editWebsite(projectName, editPrompt);

    if (!result.success) {
      addMessage('assistant', `❌ Edit failed: ${result.error}. Try rephrasing your request.`);
      setPhase('done');
      return;
    }

    const previewUrl = result.previewUrl || webgenService.getPreviewUrl(projectName);
    addMessage('assistant', '✅ Changes applied! The preview has been updated.');
    setPhase('done');
    onWebsiteGenerated(projectName, previewUrl);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (phase === 'done' && projectName) {
      handleEdit();
    } else {
      handleSubmitIdea();
    }
  };

  return (
    <div className="ai-chat-container">
      <div className="ai-chat-header">
        <div className="ai-chat-title">
          <Sparkles size={24} />
          <h2>AI Website Generator</h2>
        </div>
        {phase === 'done' && (
          <button
            className="proceed-button"
            onClick={() => { setPhase('idle'); setProjectName(''); setMessages([messages[0]]); }}
            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', marginRight: '0.5rem' }}
          >
            <RefreshCw size={16} />
            New Project
          </button>
        )}
        {onOpenGallery && (
          <button
            className="proceed-button"
            onClick={onOpenGallery}
            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)' }}
          >
            <FolderOpen size={16} />
            Past Projects
          </button>
        )}
      </div>

      <div className="ai-chat-messages">
        {messages.map(message => (
          <div key={message.id} className={`chat-message ${message.role}`}>
            <div className="message-avatar">
              {message.role === 'assistant' ? <Sparkles size={20} /> :
                message.role === 'system' ? <Loader size={20} className={phase === 'generating' || phase === 'asking' ? 'spinner' : ''} /> :
                  <div className="user-avatar">You</div>}
            </div>
            <div className="message-content">
              <p>{message.content}</p>
              <span className="message-time">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}

        {/* Questionnaire form */}
        {phase === 'questionnaire' && questions.length > 0 && (
          <div className="chat-message assistant">
            <div className="message-avatar"><Sparkles size={20} /></div>
            <div className="message-content" style={{ width: '100%' }}>
              <div style={{
                display: 'flex', flexDirection: 'column', gap: '0.75rem',
                background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '1rem',
              }}>
                {questions.map(q => {
                  const qId = q.id || q.name || `q_${Math.random()}`;
                  const qType = q.type || 'text';
                  return (
                    <div key={qId} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      <label style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 500 }}>
                        {q.label}
                      </label>
                      {(qType === 'single_select' || qType === 'select') && q.options ? (
                        <select
                          value={answers[qId] || ''}
                          onChange={e => setAnswers(prev => ({ ...prev, [qId]: e.target.value }))}
                          style={{
                            padding: '0.5rem', borderRadius: '6px', background: '#1e293b',
                            color: 'white', border: '1px solid rgba(255,255,255,0.1)',
                          }}
                        >
                          <option value="">— Select —</option>
                          {q.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                        </select>
                      ) : (qType === 'multi_select') && q.options ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                          {q.options.map(opt => {
                            const selected = (answers[qId] || '').split(',').map(s => s.trim()).includes(opt);
                            return (
                              <button
                                key={opt}
                                type="button"
                                onClick={() => {
                                  const current = (answers[qId] || '').split(',').map(s => s.trim()).filter(Boolean);
                                  const updated = selected
                                    ? current.filter(v => v !== opt)
                                    : [...current, opt];
                                  setAnswers(prev => ({ ...prev, [qId]: updated.join(', ') }));
                                }}
                                style={{
                                  padding: '0.35rem 0.7rem', borderRadius: '16px', fontSize: '0.82rem',
                                  border: selected ? '1px solid #667eea' : '1px solid rgba(255,255,255,0.15)',
                                  background: selected ? 'rgba(102,126,234,0.25)' : 'rgba(255,255,255,0.05)',
                                  color: selected ? '#a5b4fc' : '#94a3b8', cursor: 'pointer',
                                }}
                              >
                                {opt}
                              </button>
                            );
                          })}
                        </div>
                      ) : (
                        <input
                          type="text"
                          value={answers[qId] || ''}
                          onChange={e => setAnswers(prev => ({ ...prev, [qId]: e.target.value }))}
                          placeholder={q.placeholder || 'Type your answer...'}
                          style={{
                            padding: '0.5rem', borderRadius: '6px', background: '#1e293b',
                            color: 'white', border: '1px solid rgba(255,255,255,0.1)',
                          }}
                        />
                      )}
                    </div>
                  );
                })}
                <button
                  onClick={handleGenerate}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
                    padding: '0.75rem', borderRadius: '8px', border: 'none', cursor: 'pointer',
                    background: 'linear-gradient(135deg, #667eea, #764ba2)',
                    color: 'white', fontWeight: 600, fontSize: '1rem', marginTop: '0.5rem',
                  }}
                >
                  <Sparkles size={18} />
                  Generate Website
                </button>
              </div>
            </div>
          </div>
        )}

        {phase === 'generating' && (
          <div className="chat-message assistant">
            <div className="message-avatar"><Sparkles size={20} /></div>
            <div className="message-content">
              <div className="typing-indicator">
                <Loader size={16} className="spinner" />
                <span>Streaming artifacts...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="ai-chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={
            phase === 'done' ? 'Describe changes to make...' :
              phase === 'questionnaire' ? 'Or type additional details...' :
                'Describe your website idea...'
          }
          disabled={phase === 'generating' || phase === 'asking'}
        />
        <button type="submit" disabled={!input.trim() || phase === 'generating' || phase === 'asking'}>
          {phase === 'done' ? <ArrowRight size={20} /> : <Send size={20} />}
        </button>
      </form>
    </div>
  );
}
