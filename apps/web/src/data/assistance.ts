import assistanceConfig from '../../../../config/official-assistance.json';

export type AssistanceKind = 'web' | 'phone' | 'email';

export interface AssistanceChannel {
  channelId: 'portal' | 'helpline' | 'email';
  kind: AssistanceKind;
  href: string;
  labelKey: string;
  descriptionKey: string;
  actionKey: string;
}

export const assistanceSource = {
  label: assistanceConfig.source.label,
  url: assistanceConfig.source.url,
  lastVerified: assistanceConfig.source.last_verified,
  maxAgeDays: assistanceConfig.source.max_age_days
};

export const assistanceChannels: AssistanceChannel[] = assistanceConfig.channels.map((channel) => ({
  channelId: channel.channel_id as AssistanceChannel['channelId'],
  kind: channel.kind as AssistanceKind,
  href: channel.href,
  labelKey: channel.label_key,
  descriptionKey: channel.description_key,
  actionKey: channel.action_key
}));
