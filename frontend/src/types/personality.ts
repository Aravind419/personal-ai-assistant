export type CommunicationStyle = 'natural' | 'concise' | 'technical' | 'detailed';
export type FormalityLevel = 'balanced' | 'casual' | 'formal';
export type DetailLevel = 'balanced' | 'concise' | 'in_depth';
export type MemoryUsageMode = 'natural_weave' | 'minimal' | 'explicit';
export type EmojiUsage = 'minimal' | 'none' | 'expressive';

export interface AssistantPersonalityConfig {
  name: string;
  communication_style: CommunicationStyle;
  formality: FormalityLevel;
  detail_level: DetailLevel;
  memory_usage: MemoryUsageMode;
  emoji_usage: EmojiUsage;
  custom_instructions?: string | null;
}
