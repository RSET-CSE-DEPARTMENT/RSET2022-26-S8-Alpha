import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { LogOut, Plus, Clock, FileText, ChevronRight, Activity, Zap, Trash2 } from 'lucide-react';
import { format } from 'date-fns';

type Session = {
  id: string;
  raw_input: string | null;
  status: string;
  started_at: string;
};

const Dashboard = () => {
  const { user, loading: authLoading } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<{ full_name: string } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/auth');
    }
  }, [user, authLoading, navigate]);

  useEffect(() => {
    if (user) {
      fetchProfile();
      fetchSessions();
    }
  }, [user]);

  const fetchProfile = async () => {
    const { data, error } = await supabase
      .from('profiles')
      .select('full_name')
      .eq('id', user?.id)
      .single();

    if (!error && data) setProfile(data);
  };

  const fetchSessions = async () => {
    setLoading(true);
    const { data, error } = await supabase
      .from('sessions')
      .select('*')
      .eq('user_id', user?.id)
      .order('started_at', { ascending: false });

    if (error) {
      toast.error('Failed to load forensic records');
      setSessions([]);
    } else {
      setSessions(data || []);
    }
    setLoading(false);
  };

  const handleCreateSession = async () => {
    const { data, error } = await supabase
      .from('sessions')
      .insert([{ user_id: user?.id, status: 'Started' }])
      .select()
      .single();

    if (error) {
      toast.error('Initialization failed');
    } else if (data) {
      toast.success('New forensic sequence initiated');
      navigate(`/workspace/${data.id}`);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.preventDefault();
    e.stopPropagation(); 
    
    if (!window.confirm("Are you sure you want to purge this case record? This action cannot be undone.")) return;

    const { error } = await supabase
      .from('sessions')
      .delete()
      .eq('id', sessionId);

    if (error) {
      toast.error("Failed to delete case record");
      console.error(error);
    } else {
      toast.success("Case record purged successfully");
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate('/auth');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Completed': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
      case 'In Progress': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      case 'Processing': return 'bg-sky-500/10 text-sky-500 border-sky-500/20';
      default: return 'bg-slate-500/10 text-slate-500 border-slate-500/20';
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-background font-sans flex items-center justify-center relative">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,#3b82f610_0%,transparent_70%)]" />
        <div className="text-center z-10">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-primary/10 border border-primary/20 animate-pulse flex items-center justify-center">
             <Activity className="w-8 h-8 text-primary animate-bounce" />
          </div>
          <p className="text-sm font-medium tracking-widest uppercase text-muted-foreground">Synchronizing Records...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30">
      {/* 1. Command Header */}
      <header className="border-b border-white/5 bg-card/30 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20 flex items-center justify-center shadow-inner">
                <Activity className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-tight">Forensic Command Center</h1>
                <div className="flex items-center gap-2">
                   <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                   <p className="text-xs text-muted-foreground font-medium uppercase tracking-tighter">
                     Active Agent: {profile?.full_name || 'Authorized User'}
                   </p>
                </div>
              </div>
            </div>
            <Button 
              variant="ghost" 
              onClick={handleSignOut} 
              className="hover:bg-destructive/10 hover:text-destructive transition-all rounded-xl border border-transparent hover:border-destructive/20"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Terminate Session
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* 2. Main Intelligence Feed */}
          <div className="lg:col-span-8 space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold tracking-tight flex items-center gap-3">
                <FileText className="w-6 h-6 text-primary" />
                Case Archives
              </h2>
              <Badge variant="outline" className="px-3 py-1 bg-card/50 border-white/10 text-xs font-mono">
                {sessions.length} RECORD(S) FOUND
              </Badge>
            </div>
            
            {sessions.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-white/10 bg-card/20 p-20 text-center backdrop-blur-sm">
                <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-primary/5 flex items-center justify-center border border-primary/10">
                  <Zap className="w-10 h-10 text-muted-foreground/40" />
                </div>
                <h3 className="text-xl font-bold mb-2">Archive Empty</h3>
                <p className="text-muted-foreground max-w-sm mx-auto mb-8">
                  No forensic investigations have been initiated. Start your first session to begin neural reconstruction.
                </p>
                <Button onClick={handleCreateSession} size="lg" className="rounded-2xl shadow-xl shadow-primary/20 font-bold tracking-wide">
                   <Plus className="mr-2 h-5 w-5" /> Initialize First Case
                </Button>
              </div>
            ) : (
              <div className="grid gap-4">
                {sessions.map((session) => (
                  <Card
                    key={session.id}
                    className="group p-5 bg-card/40 hover:bg-card/60 border-white/5 hover:border-primary/30 cursor-pointer transition-all duration-300 rounded-2xl relative overflow-hidden backdrop-blur-md"
                    onClick={() => navigate(`/workspace/${session.id}`)}
                  >
                    <div className="flex items-center justify-between relative z-10">
                      <div className="space-y-3 flex-1">
                        <div className="flex items-center gap-4">
                          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-black/40 text-primary border border-primary/20 tracking-tighter">
                            ID: {session.id.slice(0, 8)}
                          </span>
                          <Badge className={`${getStatusColor(session.status)} border rounded-lg px-2 text-[10px] uppercase font-bold tracking-widest`}>
                            {session.status}
                          </Badge>
                        </div>
                        <p className="text-sm font-medium text-foreground/80 line-clamp-1 italic pr-12">
                          "{session.raw_input || 'Awaiting witness description...'}"
                        </p>
                        <div className="flex items-center gap-4 text-[10px] text-muted-foreground font-semibold uppercase tracking-widest">
                          <span className="flex items-center gap-1.5">
                            <Clock className="w-3 h-3" /> 
                            {format(new Date(session.started_at), 'MMM d, yyyy')}
                          </span>
                          <span className="w-1 h-1 rounded-full bg-white/20" />
                          <span>Version 1.0</span>
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 z-20 transition-colors"
                          onClick={(e) => handleDeleteSession(e, session.id)}
                          title="Delete Case"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                        <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                      </div>
                    </div>
                    {/* Hover Glow */}
                    <div className="absolute -right-20 -top-20 w-40 h-40 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-colors pointer-events-none" />
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* 3. Tactical Sidebar */}
          <div className="lg:col-span-4 space-y-6">
            <h2 className="text-2xl font-bold tracking-tight">Rapid Response</h2>
            <div className="bg-gradient-to-br from-primary/10 to-transparent p-[1px] rounded-3xl">
              <div className="bg-card/60 backdrop-blur-xl p-8 rounded-3xl border border-white/5 space-y-6 shadow-2xl">
                <div className="space-y-2">
                  <h3 className="text-sm font-bold uppercase tracking-widest text-primary">New Investigation</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Deploy a new neural reconstruction instance to process fresh witness testimony.
                  </p>
                </div>
                <Button 
                  onClick={handleCreateSession} 
                  className="w-full py-6 rounded-2xl shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all text-sm font-bold tracking-widest" 
                  size="lg"
                >
                  <Plus className="mr-2 h-5 w-5" /> INITIATE SEQUENCE
                </Button>
                
                <div className="pt-6 border-t border-white/5">
                   <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-tighter text-muted-foreground/60 mb-4">
                      <span>System Load</span>
                      <span className="text-emerald-500">Optimal</span>
                   </div>
                   <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                      <div className="w-1/3 h-full bg-primary shadow-[0_0_10px_#3b82f6]" />
                   </div>
                </div>
              </div>
            </div>
            
            {/* 4. Stats Summary */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-card/40 p-5 rounded-2xl border border-white/5 text-center transition-colors hover:bg-card/60">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter mb-1">Total Cases</p>
                <p className="text-2xl font-black text-primary font-mono">{sessions.length}</p>
              </div>
              <div className="bg-card/40 p-5 rounded-2xl border border-white/5 text-center transition-colors hover:bg-card/60">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter mb-1">Success Rate</p>
                <p className="text-2xl font-black text-emerald-500 font-mono">98%</p>
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
};

export default Dashboard;