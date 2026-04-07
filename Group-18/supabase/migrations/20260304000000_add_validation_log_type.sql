-- Add 'validation' action type to logs table and fix existing action types
ALTER TABLE public.logs
DROP CONSTRAINT logs_action_type_check;

ALTER TABLE public.logs
ADD CONSTRAINT logs_action_type_check 
  CHECK (action_type IN ('transform', 'regenerate', 'create', 'update', 'reset', 'text_refine', 'save', 'export', 'validation'));
