# Avatar JavaScript / ESM

This export uses the same .avatar.json definition as @bible-strong/avatar-react. The rendering and
playback engine is provided by @bible-strong/avatar-web instead of being copied into this export.

## Run the demo

```sh
npx serve .
```

Then open the local URL displayed by the command. index.html loads avatar-web from esm.sh and the
exported kirby.avatar.json file from this folder.

## Use in your application

```js
import { createAvatar } from '@bible-strong/avatar-web'
import definition from './kirby.avatar.json'

const avatar = createAvatar('#avatar', {
  definition,
  defaultAnimation: 'idle',
})

avatar.play('happy')
avatar.pause()
avatar.stop()
```

The JSON import is intended for a modern ESM build tool such as Vite.
