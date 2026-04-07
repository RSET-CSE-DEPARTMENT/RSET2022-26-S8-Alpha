import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { ShieldCheck, Fingerprint, Eye, Sparkles, Loader2, Brain, History, FileSearch } from 'lucide-react';

const Auth = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const redirectUrl = `${window.location.origin}/dashboard`;

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: redirectUrl,
        data: { full_name: fullName },
      },
    });

    setLoading(false);
    if (error) {
      toast.error(error.message);
    } else {
      toast.success('Access credentials provisioned. You can now sign in.');
      setEmail(''); setPassword(''); setFullName('');
    }
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);
    if (error) {
      toast.error(error.message);
    } else {
      toast.success('Biometric match confirmed. Redirecting...');
      navigate('/dashboard');
    }
  };

  return (
    <div className="min-h-screen w-full lg:grid lg:grid-cols-2 overflow-hidden bg-background">
      
      {/* --- LEFT COLUMN: Hero / Features (Hidden on mobile) --- */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 bg-zinc-900 text-white border-r border-white/10 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,#3b82f620_0%,transparent_40%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,#ffffff03_1px,transparent_1px)] bg-[size:40px_40px] opacity-20" />
        
        {/* Top Logo Area */}
        <div className="relative z-10 flex items-center gap-3 text-lg font-bold tracking-widest uppercase text-white/80">
          <ShieldCheck className="h-6 w-6 text-primary" />
          <span>F.S.A.I Protocol</span>
        </div>

        {/* Central Content */}
        <div className="relative z-10 space-y-8 max-w-lg">
          <div className="space-y-4">
            <h1 className="text-5xl font-extrabold tracking-tight leading-tight">
              Turn Description into <span className="text-primary">Digital Evidence</span>.
            </h1>
            <p className="text-lg text-zinc-400 leading-relaxed">
              Advanced Neural Forensic Sketching powered by Generative Adversarial Networks. 
              Bridging the gap between witness memory and visual identification.
            </p>
          </div>

          {/* Feature Grid */}
          <div className="grid grid-cols-1 gap-6 pt-8">
            <div className="flex items-start gap-4 p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors cursor-default">
              <div className="p-2.5 rounded-lg bg-primary/20 text-primary">
                <Brain className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-white">NLP Interpretation</h3>
                <p className="text-sm text-zinc-400 mt-1">Parses natural language testimony to extract facial feature attributes instantly.</p>
              </div>
            </div>

            <div className="flex items-start gap-4 p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors cursor-default">
              <div className="p-2.5 rounded-lg bg-emerald-500/20 text-emerald-500">
                <History className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Version Control</h3>
                <p className="text-sm text-zinc-400 mt-1">Maintain an immutable chain of custody for every sketch iteration and refinement.</p>
              </div>
            </div>

            <div className="flex items-start gap-4 p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors cursor-default">
              <div className="p-2.5 rounded-lg bg-amber-500/20 text-amber-500">
                <FileSearch className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Case Management</h3>
                <p className="text-sm text-zinc-400 mt-1">Securely archive and retrieve case files with metadata and confidence scoring.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Area */}
        <div className="relative z-10 flex justify-between items-end text-xs text-zinc-500 font-mono">
          <div>
            <p>SYSTEM STATUS: <span className="text-emerald-500">ONLINE</span></p>
            <p>VERSION: 3.0.4-ALPHA</p>
          </div>
          <div className="flex gap-4">
            <span>PRIVACY PROTOCOL</span>
            <span>TERMS OF SERVICE</span>
          </div>
        </div>
      </div>

      {/* --- RIGHT COLUMN: Auth Form --- */}
      <div className="relative flex items-center justify-center p-6 bg-background">
        {/* Cyber Background Elements for Right Side */}
        <div className="absolute inset-0 z-0">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-[120px]" />
        </div>

        <div className="w-full max-w-md z-10 space-y-8">
          {/* Brand Identity (Mobile & Desktop) */}
          <div className="text-center relative">
            <div className="relative w-20 h-20 mx-auto mb-6 group">
              <div className="absolute inset-0 bg-primary/20 rounded-2xl rotate-6 group-hover:rotate-12 transition-transform duration-500" />
              <div className="absolute inset-0 bg-primary/10 rounded-2xl -rotate-6 group-hover:-rotate-12 transition-transform duration-500" />
              <div className="relative w-full h-full rounded-2xl bg-card border border-primary/20 backdrop-blur-xl flex items-center justify-center shadow-2xl overflow-hidden">
                <Eye className="w-10 h-10 text-primary" />
                {/* Scanning bar animation */}
                <div className="absolute top-0 left-0 w-full h-[2px] bg-primary shadow-[0_0_15px_#3b82f6] animate-[scan_3s_linear_infinite]" />
              </div>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-foreground to-foreground/60">
              Agent Access
            </h1>
            <p className="text-muted-foreground mt-2 font-medium flex items-center justify-center gap-2">
              <ShieldCheck className="w-4 h-4 text-primary" />
              Secure Neural Reconstruction Portal
            </p>
          </div>

          {/* Auth Tabs */}
          <div className="bg-card/40 backdrop-blur-2xl border border-white/10 rounded-3xl p-1 shadow-[0_20px_50px_rgba(0,0,0,0.2)]">
            <Tabs defaultValue="signin" className="w-full">
              <TabsList className="grid w-full grid-cols-2 bg-transparent p-2">
                <TabsTrigger value="signin" className="rounded-2xl py-3 data-[state=active]:bg-background data-[state=active]:shadow-lg transition-all">
                  Authorize
                </TabsTrigger>
                <TabsTrigger value="signup" className="rounded-2xl py-3 data-[state=active]:bg-background data-[state=active]:shadow-lg transition-all">
                  Provision
                </TabsTrigger>
              </TabsList>

              <TabsContent value="signin" className="mt-0 p-6 pt-2">
                <form onSubmit={handleSignIn} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="signin-email" className="text-xs uppercase tracking-widest text-muted-foreground ml-1">Identifier</Label>
                    <div className="relative group">
                      <Fingerprint className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                      <Input id="signin-email" type="email" placeholder="agent@forensic.ai" className="pl-10 h-12 bg-background/50 border-white/5 focus:border-primary/50 transition-all rounded-xl" value={email} onChange={(e) => setEmail(e.target.value)} required />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signin-password" id="signin-password-label" className="text-xs uppercase tracking-widest text-muted-foreground ml-1">Access Key</Label>
                    <Input id="signin-password" type="password" placeholder="••••••••" className="h-12 bg-background/50 border-white/5 focus:border-primary/50 transition-all rounded-xl" value={password} onChange={(e) => setPassword(e.target.value)} required />
                  </div>
                  <Button type="submit" className="w-full h-12 rounded-xl bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20 text-white font-bold transition-all hover:scale-[1.02] active:scale-95" disabled={loading}>
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Request Access'}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="signup" className="mt-0 p-6 pt-2">
                <form onSubmit={handleSignUp} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="signup-name" className="text-xs uppercase tracking-widest text-muted-foreground ml-1">Full Identity</Label>
                    <Input id="signup-name" type="text" placeholder="Special Agent Doe" className="h-12 bg-background/50 border-white/5 focus:border-primary/50 transition-all rounded-xl" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-email" className="text-xs uppercase tracking-widest text-muted-foreground ml-1">New Identifier</Label>
                    <Input id="signup-email" type="email" placeholder="agent@forensic.ai" className="h-12 bg-background/50 border-white/5 focus:border-primary/50 transition-all rounded-xl" value={email} onChange={(e) => setEmail(e.target.value)} required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-password" id="signup-password-label" className="text-xs uppercase tracking-widest text-muted-foreground ml-1">Define Access Key</Label>
                    <Input id="signup-password" type="password" placeholder="Min. 6 Characters" className="h-12 bg-background/50 border-white/5 focus:border-primary/50 transition-all rounded-xl" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
                  </div>
                  <Button type="submit" className="w-full h-12 rounded-xl bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20 text-white font-bold transition-all hover:scale-[1.02] active:scale-95" disabled={loading}>
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Provision Account'}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </div>

          {/* Footer Trust Badges */}
          <div className="flex items-center justify-center gap-6 pt-4 text-muted-foreground/40">
             <div className="flex items-center gap-1.5 grayscale opacity-50"><Sparkles className="w-3.5 h-3.5" /><span className="text-[10px] font-bold uppercase tracking-tighter">Neural Engine v3.0</span></div>
             <div className="h-3 w-px bg-border/50" />
             <div className="flex items-center gap-1.5 grayscale opacity-50"><ShieldCheck className="w-3.5 h-3.5" /><span className="text-[10px] font-bold uppercase tracking-tighter">Encrypted Node</span></div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes scan {
          0% { top: 0; }
          50% { top: 100%; }
          100% { top: 0; }
        }
      `}</style>
    </div>
  );
};

export default Auth;