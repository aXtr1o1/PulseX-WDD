import type { Metadata } from 'next';
import ChatWidget from '@/components/widget/ChatWidget';

export const metadata: Metadata = {
    title: 'PulseX Widget — Wadi Degla Developments',
    description: 'Embeddable property concierge widget for WDD.',
};

interface PageProps {
    searchParams: { project?: string; region?: string; lang?: string };
}

export default function WidgetPage({ searchParams }: PageProps) {
    const project = searchParams.project;
    const region = searchParams.region;

    return (
        <div className="w-full h-screen flex flex-col bg-white">
            <ChatWidget
                initialProject={project}
                initialRegion={region}
                embedded
            />
        </div>
    );
}
