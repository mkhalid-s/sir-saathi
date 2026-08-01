import assistanceConfig from '../../../../config/official-assistance.json';

export type AssistanceKind = 'web' | 'phone' | 'email';

export interface AssistanceChannel {
  channelId: 'portal' | 'helpline' | 'email';
  kind: AssistanceKind;
  href: string;
  sourceIds: string[];
  labelKey: string;
  descriptionKey: string;
  actionKey: string;
}

export const assistanceSources = assistanceConfig.sources.map((source) => ({
  sourceId: source.source_id,
  label: source.label,
  url: source.url,
  lastVerified: source.last_verified,
  maxAgeDays: source.max_age_days
}));

export const assistanceChannels: AssistanceChannel[] = assistanceConfig.channels.map((channel) => ({
  channelId: channel.channel_id as AssistanceChannel['channelId'],
  kind: channel.kind as AssistanceKind,
  href: channel.href,
  sourceIds: channel.source_ids,
  labelKey: channel.label_key,
  descriptionKey: channel.description_key,
  actionKey: channel.action_key
}));
