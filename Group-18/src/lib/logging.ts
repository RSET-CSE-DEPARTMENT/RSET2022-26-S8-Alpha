import { supabase } from '@/integrations/supabase/client';

export type LogActionType = 'transform' | 'regenerate' | 'create' | 'update' | 'reset' | 'text_refine' | 'save' | 'export' | 'validation';

export const addSessionLog = async (
  sessionId: string,
  actionType: LogActionType,
  description: string
): Promise<void> => {
  try {
    await supabase.from('logs').insert([{
      session_id: sessionId,
      action_type: actionType,
      description: description
    }]);
  } catch (error) {
    console.error('Failed to add log:', error);
  }
};
