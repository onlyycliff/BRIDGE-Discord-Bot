import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function VoteLog() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Vote Log</h1>
      <Card>
        <CardHeader>
          <CardTitle>Vote Log</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Vote log table with search and pagination will render here.</p>
        </CardContent>
      </Card>
    </div>
  )
}
