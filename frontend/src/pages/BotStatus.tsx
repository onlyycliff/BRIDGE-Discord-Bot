import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function BotStatus() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Bot Status</h1>
      <Card>
        <CardHeader>
          <CardTitle>Bot Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Discord bot status, uptime, and activity will render here.</p>
        </CardContent>
      </Card>
    </div>
  )
}
