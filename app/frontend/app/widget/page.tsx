'use client';
import React, { useEffect, useState } from 'react';
import ChatWidget from '@/components/widget/ChatWidget';
import InitScreen from '@/components/InitScreen';

export default function WidgetPage() {
    const [ready, setReady] = useState(false);
    const [project, setProject] = useState<string>();
    const [region, setRegion] = useState<string>();

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        setProject(params.get('project') || undefined);
        setRegion(params.get('region') || undefined);
    }, []);

    return (
        <main className="w-screen h-screen bg-transparent overflow-hidden font-isidora bg-white">
            {!ready ? (
                <InitScreen onReady={() => setReady(true)} />
            ) : (
                <ChatWidget
                    embedded={true}
                    initialProject={project}
                    initialRegion={region}
                    headerLangToggle={false}
                />
            )}
        </main>
    );
}
