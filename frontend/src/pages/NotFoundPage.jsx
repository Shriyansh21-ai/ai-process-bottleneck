import { Compass } from "lucide-react";
import { Card } from "../components/ui/Card.jsx";
import { EmptyState } from "../components/ui/StateViews.jsx";
import { Link } from "../lib/router.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";

export default function NotFoundPage() {
  return (
    <>
      <PageHeader title="Page not found" />
      <Card>
        <EmptyState
          icon={Compass}
          title="This page doesn't exist"
          message="The page you're looking for may have been moved or never existed."
          action={<Link to="/" className="btn btn-primary btn-sm">Back to overview</Link>}
        />
      </Card>
    </>
  );
}
