import pygame

class OffsetGroup(pygame.sprite.LayeredUpdates):
    def __init__(self, *sprites, **kwargs):
        super().__init__(*sprites, **kwargs)
        self.offset_x = 0
        self.offset_y = 0
        self.cam_offset_x = 0
        self.cam_offset_y = 0

    def draw(self, surface):
        """draw all visible sprites in the right order onto the passed surface
        sprites are offset by the group offset
        idk how the dirty code works I just copied it lmao

        LayeredUpdates.draw(surface): return Rect_list

        """
        spritedict = self.spritedict
        surface_blit = surface.blit
        dirty = self.lostsprites
        self.lostsprites = []
        dirty_append = dirty.append
        init_rect = self._init_rect
        for cur_layer in self.layers():
            for spr in self.get_sprites_from_layer(cur_layer):
                if not spr.visible:
                    continue
                rec = spritedict[spr]
                sprite_rect = spr.rect.move(-self.offset_x, -self.offset_y)
                newrect = surface_blit(spr.image, sprite_rect)
                if rec is init_rect:
                    dirty_append(newrect)
                else:
                    if newrect.colliderect(rec):
                        dirty_append(newrect.union(rec))
                    else:
                        dirty_append(newrect)
                        dirty_append(rec)
                spritedict[spr] = newrect

        return dirty

    def set_offset(self, offset_rect):
        self.offset_x = offset_rect.x + self.cam_offset_x
        self.offset_y = offset_rect.y + self.cam_offset_y

    def set_camera_offset(self, offset_x, offset_y):
        self.cam_offset_x = offset_x
        self.cam_offset_y = offset_y

    def render(self, camera, surface):
        self.set_offset(camera)
        self.draw(surface)
