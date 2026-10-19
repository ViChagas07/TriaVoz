import { PagePlaceholder } from "@/components/PagePlaceholder";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PagePlaceholder titleKey="requests" hint={`#${id} (detail, P06)`} />;
}
