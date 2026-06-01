import { Component, OnInit, inject } from '@angular/core';
import { ChatStore } from './services/chat.store';
import { SessionListComponent } from './components/session-list/session-list';
import { ChatViewComponent } from './components/chat-view/chat-view';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [SessionListComponent, ChatViewComponent],
  template: `
    <div class="flex h-screen w-screen overflow-hidden">
      <app-session-list></app-session-list>
      <app-chat-view></app-chat-view>
    </div>
  `,
})
export class App implements OnInit {
  private store = inject(ChatStore);
  ngOnInit() {
    this.store.loadSessions().catch(() => {});
  }
}
