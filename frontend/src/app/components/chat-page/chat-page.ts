import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core';
import { ChatStore } from '../../services/chat.store';
import { SessionListComponent } from '../session-list/session-list';
import { ChatViewComponent } from '../chat-view/chat-view';

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [SessionListComponent, ChatViewComponent],
  template: `
    <div class="flex h-full min-w-0 flex-1">
      <app-session-list></app-session-list>
      <app-chat-view></app-chat-view>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatPageComponent implements OnInit {
  private store = inject(ChatStore);
  ngOnInit() {
    this.store.loadSessions().catch(() => {});
  }
}
